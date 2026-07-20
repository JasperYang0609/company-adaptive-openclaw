# Company-Adaptive OpenClaw

公司級 OpenClaw 自適應導入流程：用固定 schema 與 deterministic scripts 維護 company / department / user / workflow 四層 profile，降低不同 LLM 對執行結果的影響。


## Current status

**v1.0 automatic deliverable.** The package includes deterministic profile scripts, internal hook pack, experimental opt-in runtime profile loader, safe-default message logger, low-risk runtime hints, experimental bootstrap loader, and opt-in nightly scheduler installer.

What works now:

- Manual profile tree installation
- Profile structure validation
- Usage event logging by hook or explicit script call
- Low-risk runtime hints: immediate small preference updates and bounded per-message injection
- Full runtime profile injection via experimental bootstrap hook; disabled by default
- Nightly diff generation by scheduler or explicit script call
- Low-risk diff apply / high-risk reject gate
- Profile snapshot and rollback script
- Release test runner and hook event test

Important: hooks and cron are opt-in. This is intentional so customer installs remain reversible. After enabling hooks, restart OpenClaw Gateway once for newly discovered hooks to load.

## Modes

- `solo_team`: 小團隊 / 內部使用，不啟用 RLS。
- `client_standard`: 對外 6-15 人團隊，啟用 RLS 與敏感資料邊界。

## Quick install

```bash
python3 scripts/install_profile_tree.py --workspace /path/to/openclaw/workspace --mode solo_team --company-name "Ansai Internal"
python3 scripts/validate_profiles.py --workspace /path/to/openclaw/workspace
```

## Deterministic contract

LLM 不直接改正式 profile；只能產生 schema-bound `profile_diff`。正式寫入由 scripts 驗證、snapshot、apply、rollback。

