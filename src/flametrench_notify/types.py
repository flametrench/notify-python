# Copyright 2026 NDC Digital, LLC
# SPDX-License-Identifier: Apache-2.0

"""Notification shape and supporting types (ADR 0022)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class NotificationState(str, Enum):
    UNREAD = "unread"
    READ = "read"
    DISMISSED = "dismissed"


@dataclass(frozen=True)
class Subject:
    kind: str
    id: str


@dataclass(frozen=True)
class Notification:
    """An immutable snapshot of a notification record.

    ``id``, ``created_at``, and ``state_changed_at`` are set by the store.
    ``state`` is updated on each transition; the store returns a new instance.
    ``data`` is stored and returned verbatim — the primitive never renders it.
    """
    id: str
    scope: str
    recipient_usr_id: str
    type: str
    subject: Subject
    data: dict[str, Any]
    state: NotificationState
    created_at: datetime
    state_changed_at: datetime
