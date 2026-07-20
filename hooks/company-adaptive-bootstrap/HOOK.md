---
name: company-adaptive-bootstrap
description: "Injects a bounded adaptive profile runtime summary into BOOTSTRAP.md during agent bootstrap."
metadata:
  { "openclaw": { "emoji": "🧩", "events": ["agent:bootstrap"], "requires": { "bins": ["node"] } } }
---

# Company Adaptive Bootstrap

Loads bounded profile snippets from `adaptive-openclaw/profiles` and appends them to BOOTSTRAP.md. Disabled unless the hook is enabled.
