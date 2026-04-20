"""Tests for the SQLite storage layer."""

from __future__ import annotations

import pytest

from approvekit.models import ApprovalRequest, ApprovalStatus, AuditEntry
from approvekit.storage import Storage


@pytest.fixture()
def db():
    with Storage(":memory:") as s:
        yield s


def test_save_and_retrieve_request(db):
    req = ApprovalRequest(tool_name="send_email", tool_args={"to": "a@b.com"})
    db.save_request(req)
    fetched = db.get_request(req.id)
    assert fetched is not None
    assert fetched.tool_name == "send_email"
    assert fetched.tool_args == {"to": "a@b.com"}
    assert fetched.status == ApprovalStatus.PENDING


def test_update_request_status(db):
    req = ApprovalRequest(tool_name="delete_record", tool_args={"id": 1})
    db.save_request(req)
    req.approve(notes="ok")
    db.save_request(req)
    updated = db.get_request(req.id)
    assert updated.status == ApprovalStatus.APPROVED
    assert updated.reviewer_notes == "ok"
    assert updated.reviewed_at is not None


def test_list_pending(db):
    req1 = ApprovalRequest(tool_name="t1", tool_args={})
    req2 = ApprovalRequest(tool_name="t2", tool_args={})
    db.save_request(req1)
    db.save_request(req2)
    req1.approve()
    db.save_request(req1)
    pending = db.list_pending()
    assert len(pending) == 1
    assert pending[0].id == req2.id


def test_list_requests_by_status(db):
    req = ApprovalRequest(tool_name="t1", tool_args={})
    db.save_request(req)
    req.reject(notes="no")
    db.save_request(req)
    rejected = db.list_requests(status=ApprovalStatus.REJECTED)
    assert len(rejected) == 1
    assert rejected[0].reviewer_notes == "no"


def test_save_and_list_audit(db):
    entry = AuditEntry(
        request_id="req-1",
        tool_name="send_email",
        tool_args={"to": "x@y.com"},
        decision=ApprovalStatus.APPROVED,
        reviewer_notes="fine",
    )
    db.save_audit(entry)
    entries = db.list_audit()
    assert len(entries) == 1
    assert entries[0].tool_name == "send_email"
    assert entries[0].decision == ApprovalStatus.APPROVED
    assert entries[0].reviewer_notes == "fine"


def test_get_nonexistent_request(db):
    assert db.get_request("does-not-exist") is None


def test_list_all_requests_no_filter(db):
    for tool in ("a", "b", "c"):
        db.save_request(ApprovalRequest(tool_name=tool, tool_args={}))
    all_reqs = db.list_requests()
    assert len(all_reqs) == 3
