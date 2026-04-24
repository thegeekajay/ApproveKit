"""Tests for policy evaluation logic."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from approvekit.policy import Policy, PolicyRule


def test_exact_rule_match():
    policy = Policy.from_dict(
        {
            "rules": [
                {"tool": "send_email", "require_approval": True, "risk_level": "high"},
            ]
        }
    )
    rule = policy.evaluate("send_email")
    assert rule.require_approval is True
    assert rule.risk_level == "high"


def test_wildcard_fallback():
    policy = Policy.from_dict(
        {
            "rules": [
                {"tool": "*", "require_approval": True, "risk_level": "medium"},
            ]
        }
    )
    rule = policy.evaluate("any_unknown_tool")
    assert rule.require_approval is True


def test_permissive_default_for_unknown_tool():
    """No matching rule → permissive default (no approval required)."""
    policy = Policy.from_dict({"rules": []})
    rule = policy.evaluate("unknown_tool")
    assert rule.require_approval is False


def test_default_timeout_applied():
    policy = Policy.from_dict(
        {
            "default_timeout": 99,
            "rules": [
                {"tool": "my_tool", "require_approval": True},
            ],
        }
    )
    rule = policy.evaluate("my_tool")
    assert rule.timeout == 99


def test_rule_specific_timeout_overrides_default():
    policy = Policy.from_dict(
        {
            "default_timeout": 300,
            "rules": [
                {"tool": "my_tool", "require_approval": True, "timeout": 15},
            ],
        }
    )
    rule = policy.evaluate("my_tool")
    assert rule.timeout == 15


def test_auto_approve_flag():
    policy = Policy.from_dict(
        {
            "rules": [
                {"tool": "read_record", "require_approval": False, "auto_approve": True},
            ]
        }
    )
    rule = policy.evaluate("read_record")
    assert rule.auto_approve is True


def test_add_rule_dynamically():
    policy = Policy()
    policy.add_rule(PolicyRule(tool="new_tool", require_approval=True))
    assert policy.evaluate("new_tool").require_approval is True


def test_from_json(tmp_path):
    config = {
        "default_timeout": 30,
        "rules": [{"tool": "delete_record", "require_approval": True}],
    }
    p = tmp_path / "policy.json"
    p.write_text(json.dumps(config))
    policy = Policy.from_json(p)
    assert policy.evaluate("delete_record").require_approval is True


def test_as_dict_roundtrip():
    config = {
        "default_timeout": 60,
        "rules": [
            {"tool": "send_email", "require_approval": True, "timeout": 60, "risk_level": "high", "auto_approve": False},
        ],
    }
    policy = Policy.from_dict(config)
    d = policy.as_dict()
    assert d["default_timeout"] == 60
    assert any(r["tool"] == "send_email" for r in d["rules"])


def test_redact_fields_roundtrip():
    policy = Policy.from_dict(
        {
            "rules": [
                {
                    "tool": "send_email",
                    "require_approval": True,
                    "redact_fields": ["body", "ssn"],
                },
            ],
        }
    )

    rule = policy.evaluate("send_email")

    assert rule.redact_fields == ["body", "ssn"]
    assert policy.as_dict()["rules"][0]["redact_fields"] == ["body", "ssn"]
