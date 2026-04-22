"""
Core ApproveKit middleware.

The :class:`ApproveKit` class is the main entry point.  Wrap any callable
with :meth:`ApproveKit.guard` to automatically intercept calls, evaluate
them against the configured policy, and pause execution until a reviewer
approves, rejects, or the request times out.

Example::

    from approvekit import ApproveKit, Policy

    policy = Policy.from_dict({
        "rules": [
            {"tool": "send_email", "require_approval": True, "timeout": 120},
        ]
    })
    kit = ApproveKit(policy=policy)

    @kit.guard
    def send_email(to, subject, body):
        print(f"Sending email to {to}: {subject}")

    send_email(to="user@example.com", subject="Hello", body="Hi there")
    # → blocked until a reviewer approves via `approvekit-review`
"""

from __future__ import annotations

import functools
import inspect
import logging
import time
from typing import Any, Callable, Dict, Iterable, Optional

from approvekit.exceptions import ApprovalRejectedError, ApprovalTimeoutError
from approvekit.models import ApprovalRequest, ApprovalStatus, AuditEntry
from approvekit.policy import Policy
from approvekit.storage import Storage

logger = logging.getLogger(__name__)

# How often (seconds) the middleware polls the database for a decision.
_POLL_INTERVAL = 0.5


class ApproveKit:
    """Framework-agnostic approval middleware.

    Parameters
    ----------
    policy:
        A :class:`~approvekit.policy.Policy` instance describing which tools
        require approval and what timeouts apply.
    storage:
        A :class:`~approvekit.storage.Storage` instance.  Defaults to an
        in-memory SQLite store.
    poll_interval:
        Seconds between database polls while waiting for a reviewer decision.
    """

    def __init__(
        self,
        policy: Optional[Policy] = None,
        storage: Optional[Storage] = None,
        poll_interval: float = _POLL_INTERVAL,
    ) -> None:
        self.policy = policy or Policy()
        self.storage = storage or Storage()
        self.poll_interval = poll_interval

    # ------------------------------------------------------------------
    # Public decorator
    # ------------------------------------------------------------------

    def guard(self, fn: Callable) -> Callable:
        """Decorator that wraps *fn* with approval middleware.

        The wrapped function will:

        1. Capture its arguments.
        2. Evaluate the policy for the tool name (``fn.__name__``).
        3. If approval is **not** required (or the tool is *auto-approved*),
           call the original function immediately and log the decision.
        4. If approval **is** required, persist a :class:`ApprovalRequest`,
           then block until a reviewer decision arrives or the timeout
           expires.

        Raises
        ------
        ApprovalRejectedError
            When the reviewer explicitly rejects the request.
        ApprovalTimeoutError
            When no reviewer decision arrives within the configured timeout.
        """

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tool_name = fn.__name__
            tool_args = _capture_args(fn, args, kwargs)
            rule = self.policy.evaluate(tool_name)
            stored_args = _redact_args(tool_args, rule.redact_fields)
            policy_metadata = _policy_metadata(rule)

            logger.debug(
                "ApproveKit intercepted %s | require_approval=%s auto_approve=%s",
                tool_name,
                rule.require_approval,
                rule.auto_approve,
            )

            # --- Fast path: no approval needed ----------------------------
            if not rule.require_approval or rule.auto_approve:
                result = fn(*args, **kwargs)
                self._audit(
                    tool_name=tool_name,
                    tool_args=stored_args,
                    status=ApprovalStatus.APPROVED,
                    notes="auto-approved by policy",
                    metadata=policy_metadata,
                )
                return result

            # --- Slow path: human review required -------------------------
            req = ApprovalRequest(
                tool_name=tool_name,
                tool_args=stored_args,
                metadata=policy_metadata,
            )
            self.storage.save_request(req)
            logger.info(
                "Approval required for %s (id=%s). Waiting up to %ds.",
                tool_name,
                req.id,
                rule.timeout,
            )

            decision = self._wait_for_decision(req.id, timeout=rule.timeout)

            if decision.status == ApprovalStatus.APPROVED:
                logger.info("Request %s approved. Executing %s.", req.id, tool_name)
                self._write_audit(decision)
                return fn(*args, **kwargs)

            if decision.status == ApprovalStatus.REJECTED:
                self._write_audit(decision)
                raise ApprovalRejectedError(
                    f"Tool call '{tool_name}' was rejected by reviewer."
                    + (
                        f" Notes: {decision.reviewer_notes}"
                        if decision.reviewer_notes
                        else ""
                    )
                )

            # Timeout
            decision.mark_timeout()
            self.storage.save_request(decision)
            self._write_audit(decision)
            raise ApprovalTimeoutError(
                f"Tool call '{tool_name}' timed out after {rule.timeout}s "
                f"waiting for reviewer (request id={req.id})."
            )

        return wrapper

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _wait_for_decision(
        self, request_id: str, timeout: int
    ) -> ApprovalRequest:
        """Poll storage until the request leaves *pending* state or times out."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            req = self.storage.get_request(request_id)
            if req is not None and req.is_terminal():
                return req
            time.sleep(self.poll_interval)

        # Return the latest snapshot (still pending → caller marks timeout).
        req = self.storage.get_request(request_id)
        return req  # type: ignore[return-value]

    def _audit(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        status: ApprovalStatus,
        notes: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry = AuditEntry(
            request_id=request_id or "auto",
            tool_name=tool_name,
            tool_args=tool_args,
            decision=status,
            reviewer_notes=notes,
            metadata=metadata or {},
        )
        self.storage.save_audit(entry)

    def _write_audit(self, req: ApprovalRequest) -> None:
        entry = AuditEntry(
            request_id=req.id,
            tool_name=req.tool_name,
            tool_args=req.tool_args,
            decision=req.status,
            reviewer_notes=req.reviewer_notes,
            metadata=req.metadata,
        )
        self.storage.save_audit(entry)

    # ------------------------------------------------------------------
    # Programmatic approval helpers (useful in tests / reviewer UIs)
    # ------------------------------------------------------------------

    def approve(self, request_id: str, notes: Optional[str] = None) -> None:
        """Programmatically approve a pending request."""
        req = self._load_pending(request_id)
        req.approve(notes)
        self.storage.save_request(req)

    def reject(self, request_id: str, notes: Optional[str] = None) -> None:
        """Programmatically reject a pending request."""
        req = self._load_pending(request_id)
        req.reject(notes)
        self.storage.save_request(req)

    def _load_pending(self, request_id: str) -> ApprovalRequest:
        req = self.storage.get_request(request_id)
        if req is None:
            raise KeyError(f"No approval request found with id={request_id!r}")
        if req.is_terminal():
            raise ValueError(
                f"Request {request_id!r} is already in terminal state {req.status!r}."
            )
        return req


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def _capture_args(fn: Callable, args: tuple, kwargs: dict) -> Dict[str, Any]:
    """Bind positional and keyword arguments to a named dict for audit logging."""
    try:
        sig = inspect.signature(fn)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        return dict(bound.arguments)
    except (TypeError, ValueError):
        # Fall back to a best-effort representation.
        return {"args": list(args), "kwargs": kwargs}


def _policy_metadata(rule: Any) -> Dict[str, Any]:
    """Return policy context that should travel with the request."""
    metadata = dict(getattr(rule, "metadata", {}) or {})
    metadata.update(
        {
            "risk_level": rule.risk_level,
            "timeout": rule.timeout,
            "require_approval": rule.require_approval,
            "auto_approve": rule.auto_approve,
            "redact_fields": list(rule.redact_fields),
        }
    )
    return metadata


def _redact_args(value: Any, redact_fields: Iterable[str]) -> Any:
    """Recursively mask dict fields before storing payloads."""
    redacted = set(redact_fields)
    if not redacted:
        return value

    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if key in redacted else _redact_args(item, redacted)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [_redact_args(item, redacted) for item in value]

    if isinstance(value, tuple):
        return tuple(_redact_args(item, redacted) for item in value)

    return value
