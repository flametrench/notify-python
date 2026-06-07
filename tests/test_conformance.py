# Copyright 2026 NDC Digital, LLC
# SPDX-License-Identifier: Apache-2.0

"""Flametrench v0.4 conformance suite — Python harness for notifications.

Each test:
1. Pre-allocates fresh usr_ IDs for declared named users (``{recipient}``, etc.).
2. Creates a fresh InMemoryNotificationStore.
3. Walks the steps list, resolving {var} references from the variable map.

Matching for ``get_notification`` results is SUPERSET (result ⊇ expected):
only the fields ADR 0022 pins are asserted; server-set timestamps
(``created_at``, ``state_changed_at``) are not in the expected objects.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from flametrench_ids import generate

from flametrench_notify import (
    InMemoryNotificationStore,
    InvalidFormatError,
    NotFoundError,
    Notification,
    PreconditionError,
)

_FIXTURES_DIR = Path(__file__).parent / "conformance" / "fixtures"
_VAR_PATTERN = re.compile(r"^\{([a-z_][a-z0-9_]*)\}$")

_ERROR_CLASSES: dict[str, type[Exception]] = {
    "InvalidFormatError": InvalidFormatError,
    "NotFoundError": NotFoundError,
    "PreconditionError": PreconditionError,
}


def _load_fixture(relative_path: str) -> dict[str, Any]:
    return json.loads((_FIXTURES_DIR / relative_path).read_text(encoding="utf-8"))


def _resolve(value: Any, variables: dict[str, Any]) -> Any:
    if isinstance(value, str):
        match = _VAR_PATTERN.match(value)
        if match:
            name = match.group(1)
            if name not in variables:
                raise KeyError(f"Unknown variable in fixture: {{{name}}}")
            return variables[name]
        return value
    if isinstance(value, list):
        return [_resolve(v, variables) for v in value]
    if isinstance(value, dict):
        return {k: _resolve(v, variables) for k, v in value.items()}
    return value


def _walk_path(obj: Any, dotted_path: str) -> Any:
    current = obj
    for segment in dotted_path.split("."):
        if hasattr(current, segment):
            current = getattr(current, segment)
        elif isinstance(current, dict) and segment in current:
            current = current[segment]
        else:
            raise KeyError(
                f"Cannot resolve path segment '{segment}' on {type(current).__name__}"
            )
    return current


def _notification_to_dict(n: Notification) -> dict[str, Any]:
    return {
        "id": n.id,
        "scope": n.scope,
        "recipient_usr_id": n.recipient_usr_id,
        "type": n.type,
        "subject": {"kind": n.subject.kind, "id": n.subject.id},
        "data": n.data,
        "state": n.state.value,
    }


def _assert_superset(actual: Any, expected: Any, path: str = "") -> None:
    """Assert actual ⊇ expected (recursive subset match)."""
    if isinstance(expected, dict):
        assert isinstance(actual, dict), (
            f"at {path!r}: expected dict, got {type(actual).__name__}"
        )
        for key, exp_val in expected.items():
            assert key in actual, f"at {path!r}: missing key {key!r}"
            _assert_superset(actual[key], exp_val, f"{path}.{key}" if path else key)
    else:
        assert actual == expected, (
            f"at {path!r}: expected {expected!r}, got {actual!r}"
        )


def _invoke_op(
    store: InMemoryNotificationStore,
    op: str,
    args: dict[str, Any],
    variables: dict[str, Any],
) -> Any:
    def _recipient() -> str:
        # Use the explicit arg if provided (recipient-scope fixture); fall back
        # to the 'recipient' variable (lifecycle fixture, which pre-dates the
        # Option-2 signatures and doesn't repeat the recipient in every step).
        r = args.get("recipient_usr_id") or variables.get("recipient")
        if not r:
            raise RuntimeError(
                f"Op {op!r} requires recipient_usr_id but none supplied or in scope"
            )
        return r

    if op == "create_notification":
        return store.create_notification(
            scope=args["scope"],
            recipient_usr_id=args["recipient_usr_id"],
            type=args["type"],
            subject=args["subject"],
            data=args.get("data", {}),
        )
    if op == "get_notification":
        return store.get_notification(recipient_usr_id=_recipient(), not_id=args["id"])
    if op == "mark_read":
        return store.mark_read(recipient_usr_id=_recipient(), not_id=args["id"])
    if op == "mark_unread":
        return store.mark_unread(recipient_usr_id=_recipient(), not_id=args["id"])
    if op == "dismiss":
        return store.dismiss(recipient_usr_id=_recipient(), not_id=args["id"])
    raise RuntimeError(f"Unknown fixture op: {op!r}")


def _run_test(test: dict[str, Any]) -> None:
    store = InMemoryNotificationStore()

    # Simple single-op format: top-level `input` + `expected` (no `steps`).
    if "steps" not in test:
        inp = test["input"]
        expected = test.get("expected", {})
        if "error" in expected:
            error_class = _ERROR_CLASSES[expected["error"]]
            with pytest.raises(error_class):
                store.create_notification(
                    scope=inp["scope"],
                    recipient_usr_id=inp["recipient_usr_id"],
                    type=inp["type"],
                    subject=inp["subject"],
                    data=inp.get("data", {}),
                )
        return

    variables: dict[str, Any] = {
        name: generate("usr") for name in test.get("users", [])
    }

    for step in test["steps"]:
        op = step["op"]
        resolved_input = _resolve(step["input"], variables)

        expected = step.get("expected")
        if expected and "error" in expected:
            error_class = _ERROR_CLASSES[expected["error"]]
            with pytest.raises(error_class):
                _invoke_op(store, op, resolved_input, variables)
            continue

        result = _invoke_op(store, op, resolved_input, variables)

        if expected and "result" in expected:
            resolved_spec = _resolve(expected["result"], variables)
            actual_dict = _notification_to_dict(result)
            _assert_superset(actual_dict, resolved_spec)

        captures = step.get("captures")
        if captures:
            for name, path in captures.items():
                variables[name] = _walk_path(result, path)


def _collect_tests(relative_path: str) -> list[Any]:
    fixture = _load_fixture(relative_path)
    return [pytest.param(t, id=t["id"]) for t in fixture["tests"]]


# ─── notifications.lifecycle — state machine (ADR 0022) ───


@pytest.mark.parametrize(
    "test_case", _collect_tests("notifications/lifecycle-shape.json")
)
def test_lifecycle_shape_conformance(test_case: dict[str, Any]) -> None:
    _run_test(test_case)


# ─── notifications.recipient-scope — SDK-enforced recipient scoping (ADR 0022) ───


@pytest.mark.parametrize(
    "test_case", _collect_tests("notifications/recipient-scope.json")
)
def test_recipient_scope_conformance(test_case: dict[str, Any]) -> None:
    _run_test(test_case)


# ─── notifications.error-cases — input validation + terminal-state (ADR 0022) ──


@pytest.mark.parametrize(
    "test_case", _collect_tests("notifications/error-cases.json")
)
def test_error_cases_conformance(test_case: dict[str, Any]) -> None:
    _run_test(test_case)
