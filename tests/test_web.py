"""Tests for the local web reviewer."""

from __future__ import annotations

import json
import threading
from urllib import request
from urllib.error import HTTPError

import pytest

from approvekit.models import ApprovalRequest, ApprovalStatus, AuditEntry
from approvekit.storage import Storage
from approvekit.web import decide_request, run_server


@pytest.fixture()
def server():
    with Storage(":memory:") as storage:
        httpd = run_server(storage, "127.0.0.1", 0)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{httpd.server_port}"
        try:
            yield storage, base_url
        finally:
            httpd.shutdown()
            thread.join(timeout=2)
            httpd.server_close()


def test_list_pending_requests(server):
    storage, base_url = server
    req = ApprovalRequest(
        tool_name="send_email",
        tool_args={"to": "ceo@example.com"},
        metadata={"risk_level": "high", "timeout": 30},
    )
    storage.save_request(req)

    payload = _get_json(f"{base_url}/api/requests?status=pending")

    assert payload["requests"][0]["id"] == req.id
    assert payload["requests"][0]["tool_name"] == "send_email"
    assert payload["requests"][0]["metadata"]["risk_level"] == "high"


def test_approve_request_route(server):
    storage, base_url = server
    req = ApprovalRequest(tool_name="prod_write", tool_args={"key": "feature"})
    storage.save_request(req)

    payload = _post_json(
        f"{base_url}/api/requests/{req.id[:8]}/approve",
        {"notes": "looks safe"},
    )

    assert payload["request"]["status"] == "approved"
    saved = storage.get_request(req.id)
    assert saved is not None
    assert saved.status == ApprovalStatus.APPROVED
    assert saved.reviewer_notes == "looks safe"


def test_reject_request_route(server):
    storage, base_url = server
    req = ApprovalRequest(tool_name="delete_record", tool_args={"record_id": 7})
    storage.save_request(req)

    payload = _post_json(
        f"{base_url}/api/requests/{req.id}/reject",
        {"notes": "too risky"},
    )

    assert payload["request"]["status"] == "rejected"
    saved = storage.get_request(req.id)
    assert saved is not None
    assert saved.status == ApprovalStatus.REJECTED
    assert saved.reviewer_notes == "too risky"


def test_terminal_request_returns_conflict(server):
    storage, base_url = server
    req = ApprovalRequest(tool_name="delete_record", tool_args={})
    req.reject("already rejected")
    storage.save_request(req)

    with pytest.raises(HTTPError) as exc_info:
        _post_json(f"{base_url}/api/requests/{req.id}/approve", {})

    assert exc_info.value.code == 409


def test_audit_route(server):
    storage, base_url = server
    storage.save_audit(
        AuditEntry(
            request_id="req-1",
            tool_name="read_record",
            tool_args={"id": 42},
            decision=ApprovalStatus.APPROVED,
        )
    )

    payload = _get_json(f"{base_url}/api/audit")

    assert payload["audit"][0]["tool_name"] == "read_record"
    assert payload["audit"][0]["decision"] == "approved"


def test_decide_request_rejects_ambiguous_prefix():
    with Storage(":memory:") as storage:
        req1 = ApprovalRequest(id="abc-111", tool_name="a", tool_args={})
        req2 = ApprovalRequest(id="abc-222", tool_name="b", tool_args={})
        storage.save_request(req1)
        storage.save_request(req2)

        with pytest.raises(ValueError, match="ambiguous"):
            decide_request(storage, "abc", approve=True)


def _get_json(url: str) -> dict:
    with request.urlopen(url, timeout=3) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with request.urlopen(req, timeout=3) as response:
        return json.loads(response.read().decode("utf-8"))
