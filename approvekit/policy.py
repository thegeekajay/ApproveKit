"""Policy engine – evaluates whether a tool call requires human approval."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import yaml  # type: ignore
    _YAML_AVAILABLE = True
except ImportError:  # pragma: no cover
    _YAML_AVAILABLE = False


# Default timeout (seconds) when a rule does not specify one.
DEFAULT_TIMEOUT = 300


@dataclass
class PolicyRule:
    """A single rule that governs one or more tool names.

    Attributes:
        tool:             Exact tool name this rule applies to, or ``"*"`` to
                          match all tools not covered by a more specific rule.
        require_approval: When *True* the tool call is held until a reviewer
                          approves or the timeout expires.
        timeout:          Seconds to wait for a reviewer decision before the
                          request is automatically marked as timed-out.
        auto_approve:     When *True* the middleware immediately approves
                          without waiting for a human (useful for low-risk
                          tools that still need audit logging).
        risk_level:       Informational tag – ``"low"``, ``"medium"``, or
                          ``"high"``.
    """

    tool: str
    require_approval: bool = False
    timeout: int = DEFAULT_TIMEOUT
    auto_approve: bool = False
    risk_level: str = "low"
    metadata: Dict[str, Any] = field(default_factory=dict)


class Policy:
    """Collection of :class:`PolicyRule` objects with a lookup helper.

    Usage::

        policy = Policy.from_dict({
            "default_timeout": 120,
            "rules": [
                {"tool": "send_email", "require_approval": True, "risk_level": "high"},
                {"tool": "delete_record", "require_approval": True, "timeout": 60},
                {"tool": "read_record", "require_approval": False, "auto_approve": True},
            ]
        })
        rule = policy.evaluate("send_email")
    """

    def __init__(
        self,
        rules: Optional[List[PolicyRule]] = None,
        default_timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self._rules: Dict[str, PolicyRule] = {}
        self._wildcard: Optional[PolicyRule] = None
        self.default_timeout = default_timeout
        for rule in rules or []:
            self._add_rule(rule)

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "Policy":
        """Build a :class:`Policy` from a plain Python dictionary."""
        default_timeout = int(config.get("default_timeout", DEFAULT_TIMEOUT))
        raw_rules: List[Dict[str, Any]] = config.get("rules", [])
        rules: List[PolicyRule] = []
        for raw in raw_rules:
            rules.append(
                PolicyRule(
                    tool=raw["tool"],
                    require_approval=bool(raw.get("require_approval", False)),
                    timeout=int(raw.get("timeout", default_timeout)),
                    auto_approve=bool(raw.get("auto_approve", False)),
                    risk_level=str(raw.get("risk_level", "low")),
                    metadata={
                        k: v
                        for k, v in raw.items()
                        if k
                        not in {
                            "tool",
                            "require_approval",
                            "timeout",
                            "auto_approve",
                            "risk_level",
                        }
                    },
                )
            )
        return cls(rules=rules, default_timeout=default_timeout)

    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> "Policy":
        """Load policy from a YAML file."""
        if not _YAML_AVAILABLE:  # pragma: no cover
            raise ImportError("PyYAML is required to load policies from YAML files.")
        with open(path, "r", encoding="utf-8") as fh:
            config = yaml.safe_load(fh)
        return cls.from_dict(config or {})

    @classmethod
    def from_json(cls, path: Union[str, Path]) -> "Policy":
        """Load policy from a JSON file."""
        with open(path, "r", encoding="utf-8") as fh:
            config = json.load(fh)
        return cls.from_dict(config)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _add_rule(self, rule: PolicyRule) -> None:
        if rule.tool == "*":
            self._wildcard = rule
        else:
            self._rules[rule.tool] = rule

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(self, tool_name: str) -> PolicyRule:
        """Return the :class:`PolicyRule` that governs *tool_name*.

        Falls back to the wildcard rule (``tool="*"``), and if none exists
        returns a permissive default (no approval required).
        """
        if tool_name in self._rules:
            return self._rules[tool_name]
        if self._wildcard is not None:
            return self._wildcard
        # Permissive default – unknown tools pass without approval.
        return PolicyRule(tool=tool_name, require_approval=False)

    def add_rule(self, rule: PolicyRule) -> None:
        """Dynamically add or replace a rule."""
        self._add_rule(rule)

    def as_dict(self) -> Dict[str, Any]:
        """Serialise the policy back to a plain dictionary."""
        rules = []
        for rule in self._rules.values():
            rules.append(
                {
                    "tool": rule.tool,
                    "require_approval": rule.require_approval,
                    "timeout": rule.timeout,
                    "auto_approve": rule.auto_approve,
                    "risk_level": rule.risk_level,
                    **rule.metadata,
                }
            )
        if self._wildcard:
            rules.append(
                {
                    "tool": "*",
                    "require_approval": self._wildcard.require_approval,
                    "timeout": self._wildcard.timeout,
                    "auto_approve": self._wildcard.auto_approve,
                    "risk_level": self._wildcard.risk_level,
                }
            )
        return {"default_timeout": self.default_timeout, "rules": rules}
