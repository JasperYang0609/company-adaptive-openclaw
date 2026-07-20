# Release Checklist

## Automatic customer-deliverable gate

Run before tagging a production release:

```bash
python3 scripts/run_tests.py
node tests/hook_event_test.mjs
python3 scripts/install_auto.py --workspace /tmp/company-adaptive-release --install-hooks --install-cron --dry-run
python3 scripts/install_auto.py --workspace /tmp/company-adaptive-release --install-hooks --enable-hooks --install-cron --enable-cron --dry-run
python3 scripts/install_auto.py --workspace /tmp/company-adaptive-release --install-hooks --enable-bootstrap --dry-run
```

## Customer install command

Manual safe setup:

```bash
python3 scripts/install_profile_tree.py --workspace "$HOME/.openclaw/workspace" --mode client_standard --company-name "CLIENT_NAME"
python3 scripts/validate_profiles.py --workspace "$HOME/.openclaw/workspace"
```

Automatic setup, safe default opt-in:

```bash
python3 scripts/install_auto.py --workspace "$HOME/.openclaw/workspace" --install-hooks --enable-hooks --install-cron --enable-cron
```

Experimental bootstrap profile injection, only after canary approval:

```bash
python3 scripts/install_auto.py --workspace "$HOME/.openclaw/workspace" --install-hooks --enable-bootstrap
```

After enabling hooks, restart OpenClaw Gateway once so hooks are loaded.

## Disable / rollback

```bash
openclaw hooks disable company-adaptive-logger
openclaw hooks disable company-adaptive-bootstrap
launchctl unload ~/Library/LaunchAgents/ai.openclaw.company-adaptive.nightly.plist
python3 scripts/rollback_profile.py --workspace "$HOME/.openclaw/workspace"
```
