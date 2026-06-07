# flametrench-notify

Per-recipient notification records and lifecycle state machine for the Flametrench v0.4 platform ([ADR 0022](https://github.com/flametrench/spec/blob/main/decisions/0022-notify-primitive.md)).

## What this is

A durable, per-recipient record that something happened, with read-state (`unread ⇄ read → dismissed`). This is the *record/event* layer — not a delivery engine. Delivery (email, push, SMS) is an adopter concern; this primitive stores the notification and emits a creation event for adopters to react to.

## Install

```
pip install flametrench-notify
```

Requires Python ≥ 3.11 and `flametrench-ids >= 0.4.0`.

## Quick start

```python
from flametrench_notify import InMemoryNotificationStore

store = InMemoryNotificationStore()

n = store.create_notification(
    scope="org_0190f2a81b3c7abc8123000000000004",
    recipient_usr_id="usr_0190f2a81b3c7abc8123000000000002",
    type="comment.mention",
    subject={"kind": "doc", "id": "doc_2f9c1a..."},
    data={"actor_name": "Alice", "snippet": "…@bob take a look"},
)
# n.state == NotificationState.UNREAD

store.mark_read(n.id)
store.mark_unread(n.id)   # toggle back
store.dismiss(n.id)       # terminal
```

## License

Apache-2.0 © NDC Digital, LLC
