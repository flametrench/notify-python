# Copyright 2026 NDC Digital, LLC
# SPDX-License-Identifier: Apache-2.0

"""NotificationStore protocol (ADR 0022)."""

from __future__ import annotations

from typing import Any, Protocol

from .types import Notification


class NotificationStore(Protocol):
    """Structural protocol for a notification store (ADR 0022)."""

    def create_notification(
        self,
        *,
        scope: str,
        recipient_usr_id: str,
        type: str,
        subject: dict[str, Any],
        data: dict[str, Any],
    ) -> Notification:
        """Create a notification for a recipient.

        Returns the persisted record with state=unread.
        Emits ``notify.create`` audit event (adopter responsibility).
        Raises ``InvalidFormatError`` for malformed inputs.
        """
        ...

    def get_notification(self, *, recipient_usr_id: str, not_id: str) -> Notification:
        """Fetch a notification scoped to the authenticated recipient.

        Raises ``NotFoundError`` if not found OR if the notification belongs to
        a different recipient (indistinguishable — no cross-recipient read path).
        """
        ...

    def mark_read(self, *, recipient_usr_id: str, not_id: str) -> Notification:
        """Transition state to ``read`` for the authenticated recipient.

        Raises ``NotFoundError`` if not found or not owned by recipient.
        Raises ``PreconditionError`` if already ``dismissed``.
        """
        ...

    def mark_unread(self, *, recipient_usr_id: str, not_id: str) -> Notification:
        """Transition state to ``unread`` for the authenticated recipient.

        Raises ``NotFoundError`` if not found or not owned by recipient.
        Raises ``PreconditionError`` if already ``dismissed``.
        """
        ...

    def dismiss(self, *, recipient_usr_id: str, not_id: str) -> Notification:
        """Terminal-dismiss a notification for the authenticated recipient.

        Raises ``NotFoundError`` if not found or not owned by recipient (checked
        BEFORE state; a foreign+dismissed notification → NotFoundError, never
        PreconditionError — prevents leaking existence via error-code differential).
        Raises ``PreconditionError`` if already ``dismissed`` (own notification only).
        """
        ...
