# Status

This package is currently an **alpha safe MVP**.

## Safe for customer installation?

Yes, for manual pilot installation and review.

The package does not automatically modify OpenClaw runtime behavior after install. It creates files and scripts only.

## Not production-automatic yet

The following are intentionally not enabled in v0.1.0:

- automatic message/session monitoring
- runtime hook injection
- nightly cron scheduling
- customer setup wizard

## Production readiness gate

Before enabling for customers as an automatic system, verify:

- hook writes usage events correctly
- runtime loader only injects relevant profile snippets
- nightly job never writes high-risk fields
- rollback restores the previous profile tree
- the same test events produce deterministic applied profiles across multiple LLMs
