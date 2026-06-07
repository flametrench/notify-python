# Copyright 2026 NDC Digital, LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for InMemoryNotificationStore."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from flametrench_ids import generate

from flametrench_notify import (
    InMemoryNotificationStore,
    InvalidFormatError,
    NotFoundError,
    NotificationState,
    PreconditionError,
)

_VALID_SCOPE = "org_" + "0" * 32
_VALID_SUBJECT = {"kind": "doc", "id": "doc_abc"}


def _store() -> InMemoryNotificationStore:
    return InMemoryNotificationStore()


def _create_minimal(store: InMemoryNotificationStore, **kwargs: object):
    defaults: dict[str, object] = {
        "scope": _VALID_SCOPE,
        "recipient_usr_id": generate("usr"),
        "type": "test.event",
        "subject": _VALID_SUBJECT,
        "data": {},
    }
    defaults.update(kwargs)
    return store.create_notification(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_returns_notification_with_not_id(self):
        store = _store()
        n = _create_minimal(store)
        assert n.id.startswith("not_")
        assert len(n.id) == 36  # not_ + 32 hex

    def test_initial_state_is_unread(self):
        store = _store()
        n = _create_minimal(store)
        assert n.state == NotificationState.UNREAD

    def test_server_sets_created_at(self):
        before = datetime.now(timezone.utc)
        store = _store()
        n = _create_minimal(store)
        after = datetime.now(timezone.utc)
        assert before <= n.created_at <= after

    def test_created_at_equals_state_changed_at_on_create(self):
        store = _store()
        n = _create_minimal(store)
        assert n.created_at == n.state_changed_at

    def test_fields_stored_verbatim(self):
        store = _store()
        usr_id = generate("usr")
        subject = {"kind": "proj", "id": "proj-legacy-42"}
        data = {"actor_name": "Alice", "nested": {"x": 1}}
        n = store.create_notification(
            scope=_VALID_SCOPE,
            recipient_usr_id=usr_id,
            type="comment.mention",
            subject=subject,
            data=data,
        )
        assert n.scope == _VALID_SCOPE
        assert n.recipient_usr_id == usr_id
        assert n.type == "comment.mention"
        assert n.subject.kind == "proj"
        assert n.subject.id == "proj-legacy-42"
        assert n.data == data

    def test_each_create_unique_id(self):
        store = _store()
        ids = {_create_minimal(store).id for _ in range(5)}
        assert len(ids) == 5

    def test_notification_is_immutable(self):
        store = _store()
        n = _create_minimal(store)
        with pytest.raises((TypeError, AttributeError)):
            n.state = NotificationState.READ  # type: ignore[misc]

    def test_data_empty_dict_accepted(self):
        store = _store()
        n = _create_minimal(store, data={})
        assert n.data == {}


class TestGet:
    def test_get_returns_stored_notification(self):
        store = _store()
        created = _create_minimal(store)
        fetched = store.get_notification(created.id)
        assert fetched.id == created.id
        assert fetched.type == created.type

    def test_get_unknown_raises_not_found(self):
        store = _store()
        with pytest.raises(NotFoundError):
            store.get_notification(generate("not"))

    def test_get_preserves_all_fields(self):
        store = _store()
        usr_id = generate("usr")
        created = store.create_notification(
            scope=_VALID_SCOPE,
            recipient_usr_id=usr_id,
            type="invite.received",
            subject={"kind": "org", "id": "org_" + "a" * 32},
            data={"from": "Bob"},
        )
        fetched = store.get_notification(created.id)
        assert fetched.scope == _VALID_SCOPE
        assert fetched.recipient_usr_id == usr_id
        assert fetched.subject.kind == "org"
        assert fetched.data == {"from": "Bob"}


class TestMarkRead:
    def test_mark_read_from_unread(self):
        store = _store()
        n = _create_minimal(store)
        assert n.state == NotificationState.UNREAD
        updated = store.mark_read(n.id)
        assert updated.state == NotificationState.READ

    def test_mark_read_updates_state_changed_at(self):
        store = _store()
        n = _create_minimal(store)
        before = datetime.now(timezone.utc)
        updated = store.mark_read(n.id)
        after = datetime.now(timezone.utc)
        assert before <= updated.state_changed_at <= after

    def test_mark_read_get_reflects_new_state(self):
        store = _store()
        n = _create_minimal(store)
        store.mark_read(n.id)
        fetched = store.get_notification(n.id)
        assert fetched.state == NotificationState.READ

    def test_mark_read_from_dismissed_raises_precondition(self):
        store = _store()
        n = _create_minimal(store)
        store.dismiss(n.id)
        with pytest.raises(PreconditionError):
            store.mark_read(n.id)

    def test_mark_read_unknown_raises_not_found(self):
        store = _store()
        with pytest.raises(NotFoundError):
            store.mark_read(generate("not"))


class TestMarkUnread:
    def test_mark_unread_from_read(self):
        store = _store()
        n = _create_minimal(store)
        store.mark_read(n.id)
        updated = store.mark_unread(n.id)
        assert updated.state == NotificationState.UNREAD

    def test_mark_unread_toggle_both_directions(self):
        store = _store()
        n = _create_minimal(store)
        store.mark_read(n.id)
        store.mark_unread(n.id)
        fetched = store.get_notification(n.id)
        assert fetched.state == NotificationState.UNREAD

    def test_mark_unread_from_dismissed_raises_precondition(self):
        store = _store()
        n = _create_minimal(store)
        store.dismiss(n.id)
        with pytest.raises(PreconditionError):
            store.mark_unread(n.id)

    def test_mark_unread_unknown_raises_not_found(self):
        store = _store()
        with pytest.raises(NotFoundError):
            store.mark_unread(generate("not"))


class TestDismiss:
    def test_dismiss_from_unread(self):
        store = _store()
        n = _create_minimal(store)
        updated = store.dismiss(n.id)
        assert updated.state == NotificationState.DISMISSED

    def test_dismiss_from_read(self):
        store = _store()
        n = _create_minimal(store)
        store.mark_read(n.id)
        updated = store.dismiss(n.id)
        assert updated.state == NotificationState.DISMISSED

    def test_dismiss_is_terminal(self):
        store = _store()
        n = _create_minimal(store)
        store.dismiss(n.id)
        with pytest.raises(PreconditionError):
            store.dismiss(n.id)

    def test_dismiss_updates_state_changed_at(self):
        store = _store()
        n = _create_minimal(store)
        before = datetime.now(timezone.utc)
        updated = store.dismiss(n.id)
        after = datetime.now(timezone.utc)
        assert before <= updated.state_changed_at <= after

    def test_dismiss_unknown_raises_not_found(self):
        store = _store()
        with pytest.raises(NotFoundError):
            store.dismiss(generate("not"))


class TestValidation:
    """Error taxonomy tests — ADR 0022 §Errors."""

    # ── scope ──

    def test_scope_wrong_prefix_raises(self):
        store = _store()
        with pytest.raises(InvalidFormatError) as exc_info:
            _create_minimal(store, scope="usr_" + "0" * 32)
        assert exc_info.value.field == "scope"

    def test_scope_not_32hex_raises(self):
        store = _store()
        with pytest.raises(InvalidFormatError) as exc_info:
            _create_minimal(store, scope="org_tooshort")
        assert exc_info.value.field == "scope"

    def test_scope_uppercase_hex_rejected(self):
        store = _store()
        with pytest.raises(InvalidFormatError) as exc_info:
            _create_minimal(store, scope="org_" + "A" * 32)
        assert exc_info.value.field == "scope"

    def test_scope_valid_accepted(self):
        store = _store()
        n = _create_minimal(store, scope="org_" + "a" * 32)
        assert n.scope == "org_" + "a" * 32

    # ── recipient_usr_id ──

    def test_recipient_usr_id_wrong_prefix_raises(self):
        store = _store()
        with pytest.raises(InvalidFormatError) as exc_info:
            _create_minimal(store, recipient_usr_id="org_" + "a" * 32)
        assert exc_info.value.field == "recipient_usr_id"

    def test_recipient_usr_id_not_32hex_raises(self):
        store = _store()
        with pytest.raises(InvalidFormatError) as exc_info:
            _create_minimal(store, recipient_usr_id="usr_tooshort")
        assert exc_info.value.field == "recipient_usr_id"

    def test_recipient_usr_id_uppercase_hex_rejected(self):
        store = _store()
        with pytest.raises(InvalidFormatError) as exc_info:
            _create_minimal(store, recipient_usr_id="usr_" + "A" * 32)
        assert exc_info.value.field == "recipient_usr_id"

    def test_recipient_usr_id_valid_accepted(self):
        store = _store()
        usr_id = generate("usr")
        n = _create_minimal(store, recipient_usr_id=usr_id)
        assert n.recipient_usr_id == usr_id

    # ── type ──

    def test_type_too_long_raises(self):
        store = _store()
        with pytest.raises(InvalidFormatError) as exc_info:
            _create_minimal(store, type="a" * 65)
        assert exc_info.value.field == "type"

    def test_type_empty_raises(self):
        store = _store()
        with pytest.raises(InvalidFormatError) as exc_info:
            _create_minimal(store, type="")
        assert exc_info.value.field == "type"

    def test_type_uppercase_raises(self):
        store = _store()
        with pytest.raises(InvalidFormatError) as exc_info:
            _create_minimal(store, type="Comment.Mention")
        assert exc_info.value.field == "type"

    def test_type_valid_dotted_accepted(self):
        store = _store()
        n = _create_minimal(store, type="comment.mention")
        assert n.type == "comment.mention"

    def test_type_valid_with_hyphen_accepted(self):
        store = _store()
        n = _create_minimal(store, type="job-status.finished")
        assert n.type == "job-status.finished"

    # ── subject ──

    def test_subject_missing_kind_raises(self):
        store = _store()
        with pytest.raises(InvalidFormatError) as exc_info:
            _create_minimal(store, subject={"id": "doc-abc"})
        assert exc_info.value.field == "subject"

    def test_subject_missing_id_raises(self):
        store = _store()
        with pytest.raises(InvalidFormatError) as exc_info:
            _create_minimal(store, subject={"kind": "doc"})
        assert exc_info.value.field == "subject"

    def test_subject_not_dict_raises(self):
        store = _store()
        with pytest.raises(InvalidFormatError) as exc_info:
            _create_minimal(store, subject="doc:abc")
        assert exc_info.value.field == "subject"

    def test_subject_opaque_id_not_validated(self):
        store = _store()
        n = _create_minimal(store, subject={"kind": "job", "id": "export-job-9"})
        assert n.subject.id == "export-job-9"

    # ── data ──

    def test_data_not_dict_raises(self):
        store = _store()
        with pytest.raises(InvalidFormatError) as exc_info:
            _create_minimal(store, data="not a dict")
        assert exc_info.value.field == "data"

    def test_data_oversized_raises(self):
        store = _store()
        with pytest.raises(InvalidFormatError) as exc_info:
            _create_minimal(store, data={"x": "a" * (17 * 1024)})
        assert exc_info.value.field == "data"

    def test_data_stored_verbatim(self):
        store = _store()
        data = {"actor_name": "Alice", "snippet": "…@bob take a look"}
        n = _create_minimal(store, data=data)
        assert n.data == data
