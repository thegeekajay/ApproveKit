"""SQLite-backed persistence layer for ApproveKit."""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, List, Optional

from approvekit.models import ApprovalRequest, ApprovalStatus, AuditEntry

# ISO-8601 format used throughout storage (always stored as UTC).
_DT_FMT = "%Y-%m-%dT%H:%M:%S.%f"


def _dt_str(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    # Normalize to UTC before storing.
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.strftime(_DT_FMT)


def _str_dt(s: Optional[str]) -> Optional[datetime]:
    if s is None:
        return None
    # Return as timezone-aware UTC.
    return datetime.strptime(s, _DT_FMT).replace(tzinfo=timezone.utc)


_CREATE_REQUESTS = """
CREATE TABLE IF NOT EXISTS approval_requests (
    id           TEXT PRIMARY KEY,
    tool_name    TEXT NOT NULL,
    tool_args    TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',
    created_at   TEXT NOT NULL,
    reviewed_at  TEXT,
    reviewer_notes TEXT,
    metadata     TEXT NOT NULL DEFAULT '{}'
);
"""

_CREATE_AUDIT = """
CREATE TABLE IF NOT EXISTS audit_log (
    id             TEXT PRIMARY KEY,
    request_id     TEXT NOT NULL,
    tool_name      TEXT NOT NULL,
    tool_args      TEXT NOT NULL,
    decision       TEXT NOT NULL,
    timestamp      TEXT NOT NULL,
    reviewer_notes TEXT,
    metadata       TEXT NOT NULL DEFAULT '{}'
);
"""


class Storage:
    """Thread-safe SQLite storage for approval requests and audit entries.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file.  Pass ``":memory:"`` (the default)
        for an in-process, ephemeral store – useful for tests.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        # Use ``check_same_thread=False`` + our own lock for multi-threaded
        # access (the middleware waits in a separate polling loop).
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._migrate()

    # ------------------------------------------------------------------
    # Schema management
    # ------------------------------------------------------------------

    def _migrate(self) -> None:
        with self._write() as cur:
            cur.execute(_CREATE_REQUESTS)
            cur.execute(_CREATE_AUDIT)

    # ------------------------------------------------------------------
    # Context manager helpers
    # ------------------------------------------------------------------

    @contextmanager
    def _write(self) -> Generator[sqlite3.Cursor, None, None]:
        with self._lock:
            cur = self._conn.cursor()
            try:
                yield cur
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    @contextmanager
    def _read(self) -> Generator[sqlite3.Cursor, None, None]:
        with self._lock:
            yield self._conn.cursor()

    # ------------------------------------------------------------------
    # Approval requests
    # ------------------------------------------------------------------

    def save_request(self, req: ApprovalRequest) -> None:
        """Insert or replace an :class:`ApprovalRequest`."""
        with self._write() as cur:
            cur.execute(
                """
                INSERT OR REPLACE INTO approval_requests
                    (id, tool_name, tool_args, status,
                     created_at, reviewed_at, reviewer_notes, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    req.id,
                    req.tool_name,
                    json.dumps(req.tool_args),
                    req.status.value,
                    _dt_str(req.created_at),
                    _dt_str(req.reviewed_at),
                    req.reviewer_notes,
                    json.dumps(req.metadata),
                ),
            )

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Fetch a single :class:`ApprovalRequest` by its *id*."""
        with self._read() as cur:
            cur.execute(
                "SELECT * FROM approval_requests WHERE id = ?", (request_id,)
            )
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_request(row)

    def list_pending(self) -> List[ApprovalRequest]:
        """Return all requests that are still in *pending* status."""
        with self._read() as cur:
            cur.execute(
                "SELECT * FROM approval_requests WHERE status = 'pending'"
                " ORDER BY created_at ASC"
            )
            rows = cur.fetchall()
        return [self._row_to_request(r) for r in rows]

    def list_requests(
        self, status: Optional[ApprovalStatus] = None
    ) -> List[ApprovalRequest]:
        """Return all requests, optionally filtered by *status*."""
        with self._read() as cur:
            if status is not None:
                cur.execute(
                    "SELECT * FROM approval_requests WHERE status = ?"
                    " ORDER BY created_at ASC",
                    (status.value,),
                )
            else:
                cur.execute(
                    "SELECT * FROM approval_requests ORDER BY created_at ASC"
                )
            rows = cur.fetchall()
        return [self._row_to_request(r) for r in rows]

    # ------------------------------------------------------------------
    # Audit log
    # ------------------------------------------------------------------

    def save_audit(self, entry: AuditEntry) -> None:
        """Append an :class:`AuditEntry` to the audit log."""
        with self._write() as cur:
            cur.execute(
                """
                INSERT OR REPLACE INTO audit_log
                    (id, request_id, tool_name, tool_args, decision,
                     timestamp, reviewer_notes, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.id,
                    entry.request_id,
                    entry.tool_name,
                    json.dumps(entry.tool_args),
                    entry.decision.value,
                    _dt_str(entry.timestamp),
                    entry.reviewer_notes,
                    json.dumps(entry.metadata),
                ),
            )

    def list_audit(self) -> List[AuditEntry]:
        """Return all audit entries, oldest first."""
        with self._read() as cur:
            cur.execute("SELECT * FROM audit_log ORDER BY timestamp ASC")
            rows = cur.fetchall()
        return [self._row_to_audit(r) for r in rows]

    # ------------------------------------------------------------------
    # Row → dataclass helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_request(row: sqlite3.Row) -> ApprovalRequest:
        return ApprovalRequest(
            id=row["id"],
            tool_name=row["tool_name"],
            tool_args=json.loads(row["tool_args"]),
            status=ApprovalStatus(row["status"]),
            created_at=_str_dt(row["created_at"]),  # type: ignore[arg-type]
            reviewed_at=_str_dt(row["reviewed_at"]),
            reviewer_notes=row["reviewer_notes"],
            metadata=json.loads(row["metadata"]),
        )

    @staticmethod
    def _row_to_audit(row: sqlite3.Row) -> AuditEntry:
        return AuditEntry(
            id=row["id"],
            request_id=row["request_id"],
            tool_name=row["tool_name"],
            tool_args=json.loads(row["tool_args"]),
            decision=ApprovalStatus(row["decision"]),
            timestamp=_str_dt(row["timestamp"]),  # type: ignore[arg-type]
            reviewer_notes=row["reviewer_notes"],
            metadata=json.loads(row["metadata"]),
        )

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()

    def __enter__(self) -> "Storage":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
