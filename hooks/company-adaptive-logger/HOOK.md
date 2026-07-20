---
name: company-adaptive-logger
description: "Logs redacted OpenClaw message events into adaptive-openclaw/events/usage_events.jsonl."
metadata:
  { "openclaw": { "emoji": "🧭", "events": ["message:received", "message:sent"], "requires": { "bins": ["node"] } } }
---

# Company Adaptive Logger

Telemetry-only hook. It writes redacted usage events and never pushes user-visible messages.
