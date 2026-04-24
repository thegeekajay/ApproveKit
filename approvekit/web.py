"""Local browser reviewer for ApproveKit approval requests."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from approvekit.models import ApprovalRequest, ApprovalStatus, AuditEntry
from approvekit.storage import Storage


def make_handler(storage: Storage) -> type[BaseHTTPRequestHandler]:
    """Create a request handler bound to a specific storage instance."""

    class ApproveKitWebHandler(BaseHTTPRequestHandler):
        server_version = "ApproveKitWeb/0.1"

        def do_GET(self) -> None:  # noqa: N802 - stdlib hook
            parsed = urlparse(self.path)

            if parsed.path == "/":
                self._send_html(_INDEX_HTML)
                return

            if parsed.path == "/api/health":
                self._send_json({"ok": True})
                return

            if parsed.path == "/api/requests":
                params = parse_qs(parsed.query)
                status = params.get("status", ["pending"])[0]
                requests = _list_requests(storage, status)
                self._send_json({"requests": [_request_dict(req) for req in requests]})
                return

            if parsed.path == "/api/audit":
                entries = storage.list_audit()
                self._send_json({"audit": [_audit_dict(entry) for entry in entries]})
                return

            self._send_error(HTTPStatus.NOT_FOUND, "Route not found")

        def do_POST(self) -> None:  # noqa: N802 - stdlib hook
            parsed = urlparse(self.path)
            parts = [part for part in parsed.path.split("/") if part]

            if len(parts) == 4 and parts[:2] == ["api", "requests"]:
                request_id = parts[2]
                action = parts[3]
                payload = self._read_json_body()
                notes = payload.get("notes") if isinstance(payload.get("notes"), str) else None

                try:
                    if action == "approve":
                        req = decide_request(storage, request_id, approve=True, notes=notes)
                    elif action == "reject":
                        req = decide_request(storage, request_id, approve=False, notes=notes)
                    else:
                        self._send_error(HTTPStatus.NOT_FOUND, "Unknown action")
                        return
                except KeyError as exc:
                    self._send_error(HTTPStatus.NOT_FOUND, str(exc))
                    return
                except ValueError as exc:
                    self._send_error(HTTPStatus.CONFLICT, str(exc))
                    return

                self._send_json({"request": _request_dict(req)})
                return

            self._send_error(HTTPStatus.NOT_FOUND, "Route not found")

        def log_message(self, format: str, *args: Any) -> None:
            """Silence default access logs; the UI is local and chatty."""

        def _read_json_body(self) -> Dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length <= 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            if not raw:
                return {}
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                return {}
            return payload if isinstance(payload, dict) else {}

        def _send_html(self, body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _send_json(
            self, payload: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK
        ) -> None:
            encoded = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _send_error(self, status: HTTPStatus, message: str) -> None:
            self._send_json({"error": message}, status=status)

    return ApproveKitWebHandler


def decide_request(
    storage: Storage,
    request_id: str,
    *,
    approve: bool,
    notes: Optional[str] = None,
) -> ApprovalRequest:
    """Approve or reject a pending request by id or unique prefix."""
    req = _find_request(storage, request_id)
    if req is None:
        raise KeyError(f"Request {request_id!r} not found")
    if req.is_terminal():
        raise ValueError(f"Request {req.id!r} is already {req.status.value}")

    if approve:
        req.approve(notes)
    else:
        req.reject(notes)

    storage.save_request(req)
    return req


def run_server(storage: Storage, host: str, port: int) -> HTTPServer:
    """Create an HTTP server for the local reviewer."""
    return HTTPServer((host, port), make_handler(storage))


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Local ApproveKit web reviewer.")
    parser.add_argument(
        "--db",
        default=":memory:",
        help="Path to the ApproveKit SQLite database.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind.")
    args = parser.parse_args(argv)

    with Storage(db_path=args.db) as storage:
        server = run_server(storage, args.host, args.port)
        url = f"http://{args.host}:{server.server_port}"
        print(f"ApproveKit reviewer running at {url}")
        print("Press Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping reviewer.")
        finally:
            server.server_close()


def _list_requests(storage: Storage, status: str) -> list[ApprovalRequest]:
    if status == "all":
        return storage.list_requests()
    try:
        approval_status = ApprovalStatus(status)
    except ValueError:
        approval_status = ApprovalStatus.PENDING
    return storage.list_requests(status=approval_status)


def _find_request(storage: Storage, request_id: str) -> Optional[ApprovalRequest]:
    req = storage.get_request(request_id)
    if req is not None:
        return req

    matches = [req for req in storage.list_requests() if req.id.startswith(request_id)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"Request prefix {request_id!r} is ambiguous")
    return None


def _request_dict(req: ApprovalRequest) -> Dict[str, Any]:
    return {
        "id": req.id,
        "tool_name": req.tool_name,
        "tool_args": req.tool_args,
        "status": req.status.value,
        "created_at": _dt(req.created_at),
        "reviewed_at": _dt(req.reviewed_at),
        "reviewer_notes": req.reviewer_notes,
        "metadata": req.metadata,
    }


def _audit_dict(entry: AuditEntry) -> Dict[str, Any]:
    return {
        "id": entry.id,
        "request_id": entry.request_id,
        "tool_name": entry.tool_name,
        "tool_args": entry.tool_args,
        "decision": entry.decision.value,
        "timestamp": _dt(entry.timestamp),
        "reviewer_notes": entry.reviewer_notes,
        "metadata": entry.metadata,
    }


def _dt(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value is not None else None


_INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ApproveKit Reviewer</title>
  <style>
    :root {
      --bg: #f6f8fb;
      --surface: #ffffff;
      --line: #d9e2ef;
      --line-strong: #b8c6da;
      --text: #111827;
      --muted: #5f6b7a;
      --blue: #2563eb;
      --green: #16803c;
      --red: #c0262d;
      --amber: #b7791f;
      --shadow: 0 8px 28px rgba(15, 23, 42, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    header {
      border-bottom: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.92);
      position: sticky;
      top: 0;
      z-index: 10;
    }
    .topbar {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      min-height: 64px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    .brand strong { display: block; font-size: 1rem; }
    .brand span { color: var(--muted); font-size: 0.88rem; }
    main {
      width: min(1180px, calc(100% - 32px));
      margin: 28px auto 56px;
      display: grid;
      grid-template-columns: minmax(0, 1.4fr) minmax(320px, 0.8fr);
      gap: 20px;
    }
    section {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      min-width: 0;
    }
    .section-head {
      padding: 18px 20px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    h1, h2, h3, p { margin: 0; }
    h2 { font-size: 1rem; }
    .muted { color: var(--muted); font-size: 0.9rem; }
    .queue, .audit { padding: 16px; display: grid; gap: 12px; }
    .request {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      display: grid;
      gap: 12px;
      background: #fff;
    }
    .request-head {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
    }
    .tool { font-weight: 750; font-size: 1rem; }
    .meta { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
    .pill {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      border-radius: 999px;
      border: 1px solid var(--line);
      padding: 2px 9px;
      font-size: 0.76rem;
      color: var(--muted);
      background: #f8fafc;
    }
    .risk-high { color: var(--red); border-color: #f1b8bd; background: #fff1f2; }
    .risk-medium { color: var(--amber); border-color: #f3d29c; background: #fff8e7; }
    pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #0f172a;
      color: #dbeafe;
      padding: 12px;
      font-size: 0.82rem;
      line-height: 1.45;
      overflow: auto;
    }
    textarea {
      width: 100%;
      min-height: 70px;
      border: 1px solid var(--line-strong);
      border-radius: 8px;
      padding: 10px 12px;
      resize: vertical;
      font: inherit;
    }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; }
    button {
      border: 1px solid transparent;
      border-radius: 8px;
      padding: 9px 13px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }
    .approve { background: var(--green); color: #fff; }
    .reject { background: #fff; color: var(--red); border-color: #f1b8bd; }
    .refresh { background: var(--text); color: #fff; }
    .audit-row {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      display: grid;
      gap: 4px;
      background: #fff;
    }
    .status-approved { color: var(--green); }
    .status-rejected, .status-timeout { color: var(--red); }
    .empty { color: var(--muted); padding: 10px 0; }
    @media (max-width: 860px) {
      main { grid-template-columns: 1fr; }
      .topbar { align-items: flex-start; flex-direction: column; padding: 14px 0; }
    }
  </style>
</head>
<body>
  <header>
    <div class="topbar">
      <div class="brand">
        <strong>ApproveKit Reviewer</strong>
        <span>Local approval inbox for risky agent actions</span>
      </div>
      <button class="refresh" id="refresh">Refresh</button>
    </div>
  </header>
  <main>
    <section>
      <div class="section-head">
        <div>
          <h2>Pending approvals</h2>
          <p class="muted" id="queue-count">Loading...</p>
        </div>
      </div>
      <div class="queue" id="queue"></div>
    </section>
    <section>
      <div class="section-head">
        <div>
          <h2>Audit trail</h2>
          <p class="muted">Latest decisions from this database</p>
        </div>
      </div>
      <div class="audit" id="audit"></div>
    </section>
  </main>
  <script>
    const queue = document.getElementById("queue");
    const audit = document.getElementById("audit");
    const count = document.getElementById("queue-count");
    const refresh = document.getElementById("refresh");

    function pretty(value) {
      return JSON.stringify(value || {}, null, 2);
    }

    function riskClass(value) {
      if (value === "high") return "pill risk-high";
      if (value === "medium") return "pill risk-medium";
      return "pill";
    }

    function renderRequest(req) {
      const risk = req.metadata?.risk_level || "low";
      const timeout = req.metadata?.timeout || "-";
      const el = document.createElement("article");
      el.className = "request";
      el.innerHTML = `
        <div class="request-head">
          <div>
            <div class="tool">${req.tool_name}</div>
            <div class="muted">${req.id}</div>
            <div class="meta">
              <span class="${riskClass(risk)}">risk: ${risk}</span>
              <span class="pill">timeout: ${timeout}s</span>
              <span class="pill">status: ${req.status}</span>
            </div>
          </div>
        </div>
        <pre>${pretty(req.tool_args)}</pre>
        <textarea placeholder="Reviewer notes"></textarea>
        <div class="actions">
          <button class="approve">Approve</button>
          <button class="reject">Reject</button>
        </div>
      `;
      const notes = el.querySelector("textarea");
      el.querySelector(".approve").addEventListener("click", () => decide(req.id, "approve", notes.value));
      el.querySelector(".reject").addEventListener("click", () => decide(req.id, "reject", notes.value));
      return el;
    }

    function renderAudit(entry) {
      const el = document.createElement("article");
      el.className = "audit-row";
      el.innerHTML = `
        <strong>${entry.tool_name}</strong>
        <span class="status-${entry.decision}">${entry.decision}</span>
        <span class="muted">${entry.timestamp || ""}</span>
        <span class="muted">${entry.reviewer_notes || ""}</span>
      `;
      return el;
    }

    async function load() {
      const [requestsRes, auditRes] = await Promise.all([
        fetch("/api/requests?status=pending"),
        fetch("/api/audit")
      ]);
      const requests = await requestsRes.json();
      const auditPayload = await auditRes.json();

      queue.replaceChildren();
      const pending = requests.requests || [];
      count.textContent = `${pending.length} pending request${pending.length === 1 ? "" : "s"}`;
      if (pending.length === 0) {
        queue.innerHTML = `<p class="empty">No pending approvals. The agent will create requests here when it reaches a risky action.</p>`;
      } else {
        pending.forEach(req => queue.appendChild(renderRequest(req)));
      }

      audit.replaceChildren();
      const entries = (auditPayload.audit || []).slice().reverse();
      if (entries.length === 0) {
        audit.innerHTML = `<p class="empty">No audit entries yet.</p>`;
      } else {
        entries.slice(0, 12).forEach(entry => audit.appendChild(renderAudit(entry)));
      }
    }

    async function decide(id, action, notes) {
      await fetch(`/api/requests/${id}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes })
      });
      await load();
    }

    refresh.addEventListener("click", load);
    load();
    setInterval(load, 2500);
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
