# Changelog

## 0.4.0 — 2026-06-07

Initial release — Flametrench v0.4 notification primitive (ADR 0022).

- `Notification` entity: `not_<32hex>` id, scope, recipient, type, subject, data, state
- `NotificationState` enum: `unread`, `read`, `dismissed`
- `Subject` dataclass: opaque `kind` + `id`
- `InMemoryNotificationStore`: full state machine (`unread ⇄ read → dismissed`), all ADR 0022 §Errors validation
- `NotificationStore` protocol
- Cross-cutting error taxonomy: `InvalidFormatError(field)`, `PreconditionError`, `NotFoundError`
- Conformance tests: `notifications/lifecycle-shape.json` (4 tests, ADR 0022 §Lifecycle)
- Unit tests: create, get, state transitions, validation error paths
