# Status

Current release status: **v1.0 automatic deliverable**.

## Safe for customer installation?

Yes, if installed with the documented opt-in commands.

The automatic components are reversible:

- Hooks can be disabled with `openclaw hooks disable`.
- Nightly scheduler can be unloaded with `launchctl unload` on macOS.
- Profile changes can be reverted with `rollback_profile.py`.

## Included automatic components

- `company-adaptive-logger`: records redacted usage events from `message:received` and `message:sent`.
- `company-adaptive-runtime-hints`: immediately learns low-risk preferences and injects at most 5 short hints during `message:preprocessed`.
- `company-adaptive-bootstrap`: experimental; injects bounded adaptive profile context during `agent:bootstrap`; disabled by default.
- `nightly_company_adaptive.sh`: runs nightly learning, self-repair, adoption report, low-risk apply, and validation.

## Production safety boundaries

- LLMs do not directly edit official profiles.
- All writes go through deterministic scripts.
- High-risk paths are rejected or pending.
- Sensitive raw details are redacted / summarized.
- Hooks and cron are opt-in and can be disabled.

## v1.1 Runtime Hints

`company-adaptive-runtime-hints` is now part of the safe default automation:

- Immediate small updates: explicit low-risk preference corrections are written to `adaptive-openclaw/runtime_hints/discord_<id>.json`.
- Next-message application: at `message:preprocessed`, up to 5 short hints are prepended to the agent body.
- Allowed hint categories: length, format, tone, ask-before behavior, common output shape.
- Forbidden: identity, department, permissions, RLS, secrets, customer details, salary, medical, contract, or raw sensitive content.
- Full bootstrap profile injection remains experimental and disabled by default.

## v1.2 Channel Onboarding Agent

Added first-class channel profile support for customer Discord onboarding:

- `channel_profile.v1` template and schema
- deterministic `bootstrap_channel_onboarding.py`
- validation/install support for `profiles/channels/_template.md`
- logger support for channel-created events when available
- nightly channel recommendation diffs
- runtime hints and optional bootstrap awareness of channel profiles
