# Copyright 2026 NDC Digital, LLC
# SPDX-License-Identifier: Apache-2.0

"""NotificationStore error taxonomy (cross-cutting, ADR 0022 §Errors).

Uniform taxonomy shared with audit, identity, and tenancy:
- ``InvalidFormatError`` — shape/value violation; carries a ``field``
  discriminator naming the offending input.
- ``PreconditionError`` — state-machine precondition failed (e.g. transitioning
  out of ``dismissed``, which is terminal).
- ``NotFoundError`` — notification does not exist, OR the caller does not own
  the notification (non-inference: both cases raise the same error with no
  observable difference).

Opacity: ``type`` content, ``subject.id``, and ``data`` values are never
validated by the primitive beyond size/structure.
"""

from __future__ import annotations


class NotificationError(Exception):
    """Base class for all flametrench-notify errors."""


class InvalidFormatError(NotificationError):
    """An input value violates the Notification shape contract (ADR 0022 §Errors).

    ``field`` names the offending input:
    - ``"type"``             — outside ``^[a-z0-9._-]{1,64}$``
    - ``"data"``             — not a JSON object, or > 16 KB
    - ``"recipient_usr_id"`` — not a valid ``usr_<32hex>``
    - ``"scope"``            — not a valid ``org_<32hex>``
    - ``"subject"``          — missing ``kind`` or ``id``, or wrong shape
    """

    def __init__(self, field: str, message: str = "") -> None:
        self.field = field
        super().__init__(message or f"Invalid value for field: {field!r}")


class PreconditionError(NotificationError):
    """A state-machine precondition for the transition was not met.

    Raised when attempting any transition out of ``dismissed`` (terminal).
    """


class NotFoundError(NotificationError):
    """Raised when a notification does not exist or is not owned by the caller.

    Non-inference rule: cross-recipient probes raise the same error as
    non-existent notifications — no presence/count/error-code differential.
    """
