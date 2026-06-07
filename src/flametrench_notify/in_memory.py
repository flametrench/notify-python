# Copyright 2026 NDC Digital, LLC
# SPDX-License-Identifier: Apache-2.0

"""InMemoryNotificationStore — spec-conformant in-memory NotificationStore."""

from __future__ import annotations

import dataclasses
import json
import re
from datetime import datetime, timezone
from typing import Any

from flametrench_ids import generate

from .errors import InvalidFormatError, NotFoundError, PreconditionError
from .types import Notification, NotificationState, Subject

_TYPE_RE = re.compile(r"^[a-z0-9._-]{1,64}$")
_USR_ID_RE = re.compile(r"^usr_[0-9a-f]{32}$")
_ORG_ID_RE = re.compile(r"^org_[0-9a-f]{32}$")
_MAX_DATA_BYTES = 16 * 1024  # 16 KB per ADR 0022


def _validate_create(
    scope: str,
    recipient_usr_id: str,
    type: str,
    subject: dict[str, Any],
    data: dict[str, Any],
) -> Subject:
    """Validate create inputs; return parsed Subject. Raises InvalidFormatError."""
    if not _ORG_ID_RE.match(scope):
        raise InvalidFormatError("scope")

    if not _USR_ID_RE.match(recipient_usr_id):
        raise InvalidFormatError("recipient_usr_id")

    if not _TYPE_RE.match(type):
        raise InvalidFormatError("type")

    if (
        not isinstance(subject, dict)
        or not isinstance(subject.get("kind"), str)
        or not isinstance(subject.get("id"), str)
        or len(subject) < 2
    ):
        raise InvalidFormatError("subject")

    if not isinstance(data, dict):
        raise InvalidFormatError("data")
    if len(json.dumps(data).encode()) > _MAX_DATA_BYTES:
        raise InvalidFormatError("data")

    return Subject(kind=subject["kind"], id=subject["id"])


class InMemoryNotificationStore:
    """Append-only in-memory NotificationStore.

    Events are held in a dict keyed by ``not_<32hex>`` wire id.
    State transitions create new frozen ``Notification`` instances.
    ``create_notification`` validates all inputs before storing (ADR 0022 §Errors).
    """

    def __init__(self) -> None:
        self._notifications: dict[str, Notification] = {}

    def create_notification(
        self,
        *,
        scope: str,
        recipient_usr_id: str,
        type: str,
        subject: dict[str, Any],
        data: dict[str, Any],
    ) -> Notification:
        parsed_subject = _validate_create(scope, recipient_usr_id, type, subject, data)
        now = datetime.now(timezone.utc)
        not_id = generate("not")
        notification = Notification(
            id=not_id,
            scope=scope,
            recipient_usr_id=recipient_usr_id,
            type=type,
            subject=parsed_subject,
            data=data,
            state=NotificationState.UNREAD,
            created_at=now,
            state_changed_at=now,
        )
        self._notifications[not_id] = notification
        return notification

    def get_notification(self, *, recipient_usr_id: str, not_id: str) -> Notification:
        return self._get_owned(recipient_usr_id, not_id)

    def mark_read(self, *, recipient_usr_id: str, not_id: str) -> Notification:
        return self._transition(recipient_usr_id, not_id, NotificationState.READ)

    def mark_unread(self, *, recipient_usr_id: str, not_id: str) -> Notification:
        return self._transition(recipient_usr_id, not_id, NotificationState.UNREAD)

    def dismiss(self, *, recipient_usr_id: str, not_id: str) -> Notification:
        return self._transition(recipient_usr_id, not_id, NotificationState.DISMISSED)

    def _get_owned(self, recipient_usr_id: str, not_id: str) -> Notification:
        """Fetch a notification, enforcing recipient ownership.

        Returns the notification iff it exists AND belongs to recipient_usr_id.
        Both "not found" and "wrong recipient" resolve to the same NotFoundError
        — no cross-recipient read path (ADR 0022 §Access + §Tenancy non-inference).
        """
        notification = self._notifications.get(not_id)
        if notification is None or notification.recipient_usr_id != recipient_usr_id:
            raise NotFoundError(f"Notification not found: {not_id!r}")
        return notification

    def _transition(
        self, recipient_usr_id: str, not_id: str, new_state: NotificationState
    ) -> Notification:
        # Existence + ownership check FIRST — a foreign+dismissed notification
        # must raise NotFoundError, not PreconditionError (ADR 0022 §Errors /
        # "Existence/ownership check takes precedence over state-machine validation").
        notification = self._get_owned(recipient_usr_id, not_id)
        if notification.state == NotificationState.DISMISSED:
            raise PreconditionError(
                f"Notification {not_id!r} is dismissed and accepts no further transitions"
            )
        updated = dataclasses.replace(
            notification,
            state=new_state,
            state_changed_at=datetime.now(timezone.utc),
        )
        self._notifications[not_id] = updated
        return updated
