---
name: company-adaptive-runtime-hints
description: "Immediately learns low-risk user preference hints and injects short bounded hints into the next agent message."
metadata:
  { "openclaw": { "emoji": "⚡", "events": ["message:received", "message:preprocessed"], "requires": { "bins": ["node"] } } }
---

# Company Adaptive Runtime Hints

Safe runtime personalization hook.

- Learns only low-risk preferences from explicit user corrections.
- Stores at most 5 short hints per user.
- Injects only short runtime hints into `message:preprocessed`.
- Never stores identity, permissions, secrets, customer details, salary, medical, contract, or raw sensitive content.
