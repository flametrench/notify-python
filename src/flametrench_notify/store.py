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

    def get_notification(self, not_id: str) -> Notification:
        """Fetch a notification by id.

        Raises ``NotFoundError`` if not found or caller is not the recipient.
        """
        ...

    def mark_read(self, not_id: str) -> Notification:
        """Transition state to ``read``.

        Raises ``NotFoundError`` if not found.
        Raises ``PreconditionError`` if already ``dismissed``.
        """
        ...

    def mark_unread(self, not_id: str) -> Notification:
        """Transition state to ``unread``.

        Raises ``NotFoundError`` if not found.
        Raises ``PreconditionError`` if already ``dismissed``.
        """
        ...

    def dismiss(self, not_id: str) -> Notification:
        """Terminal-dismiss a notification.

        Raises ``NotFoundError`` if not found.
        Raises ``PreconditionError`` if already ``dismissed``.
        """
        ...
