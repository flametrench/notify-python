# Copyright 2026 NDC Digital, LLC
# SPDX-License-Identifier: Apache-2.0

"""flametrench-notify — per-recipient notification records and lifecycle (ADR 0022).

The spec-normative notification layer for Flametrench v0.4. See the upstream
specification at https://github.com/flametrench/spec/blob/main/decisions/0022-notify-primitive.md.

Each Notification is a durable, per-recipient record with a small read-state
machine: unread ⇄ read → dismissed (terminal). The primitive is a record/event
store — delivery, templating, and provider integration are adopter concerns.
"""

from .errors import InvalidFormatError, NotFoundError, NotificationError, PreconditionError
from .in_memory import InMemoryNotificationStore
from .store import NotificationStore
from .types import (
    Notification,
    NotificationState,
    Subject,
)

__all__ = [
    "InMemoryNotificationStore",
    "InvalidFormatError",
    "Notification",
    "NotificationError",
    "NotificationState",
    "NotificationStore",
    "NotFoundError",
    "PreconditionError",
    "Subject",
]

__version__ = "0.4.0"
