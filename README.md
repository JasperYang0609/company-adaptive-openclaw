# Company-Adaptive OpenClaw

公司級 OpenClaw 自適應導入流程：用固定 schema 與 deterministic scripts 維護 company / department / user / workflow 四層 profile，降低不同 LLM 對執行結果的影響。

開發者應累積到可驗證版本並先執行 `bash scripts/check_push.sh` 才 push。非 `main` 分支跑聚焦 Branch Check；pull request／`main` 跑完整 CI；已有 open PR 時不重跑 branch tests，同分支或 PR 的舊 run 會自動取消，真正失敗通知保留。


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
- Privacy-minimal, explicit-adapter Skill lifecycle telemetry and aggregate reporting

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


## Telemetry privacy boundary

Raw sender/channel identifiers stay inside the local `adaptive-openclaw/events` store because profile learning needs stable local references. Do not share that JSONL file with developers or external systems.

Use the safe outputs instead:

```bash
python3 scripts/generate_adoption_report.py --workspace /path/to/openclaw/workspace
python3 scripts/export_usage_events.py --workspace /path/to/openclaw/workspace
```

Both paths tolerate and count invalid legacy lines. Reports and exports use stable per-workspace pseudonymous aliases; safe exports exclude raw identifiers, session keys, channel names, and content summaries. The local export salt is created with owner-only permissions and must not be committed or bundled.

### Skill lifecycle telemetry (explicit adapter only)

Owned adapters can record `shown / selected / started / completed / failed / abandoned / corrected` without sender, channel, session, message, prompt, customer, path, stack-trace, or free-form error fields:

```bash
python3 scripts/log_skill_lifecycle.py new-journey
python3 scripts/log_skill_lifecycle.py record --workspace /path/to/workspace --journey-id jrn_... --skill-key summary-backup --stage shown --source recommendation
python3 scripts/generate_skill_lifecycle_report.py --workspace /path/to/workspace
```

Coverage is **`explicit_adapter_only`**. Missing events do not prove that a Skill was not shown or used, and this Repository does not patch or automatically instrument OpenClaw Core. Reports contain aggregate categorical counts only. See `references/skill_lifecycle_telemetry.md`.

## v1.1 Runtime Hints

Safe default automation now includes immediate low-risk runtime hints:

```text
User correction -> runtime_hints json -> next message gets at most 5 short hints -> nightly job consolidates into profiles.
```

This gives users the feeling that OpenClaw immediately remembers preferences without injecting full profiles into the model context.

## v1.2 Channel Onboarding Agent

This package now supports a channel-level adaptive layer for customer Discord channel/thread onboarding.

Core idea:

```text
new channel -> channel profile -> creator role/position -> role-aware assistance menu -> first visible artifact -> nightly optimization
```

Use cases:

- Detect a new channel's likely scene from name/category/topic.
- Remember the channel creator's user id, identity, role/position, and bounded context.
- Avoid asking customers to write prompts from scratch.
- Ask "依照你的角色，我可以協助你以下問題，你想先從哪個開始？"
- Produce a first visible artifact, then learn from acceptance/corrections.

Deterministic entry point:

```bash
python3 scripts/bootstrap_channel_onboarding.py \
  --workspace /path/to/openclaw/workspace \
  --channel-id 123456789 \
  --channel-name "客服" \
  --created-by-user-id 960433085042798623 \
  --creator-role "主管" \
  --creator-position "客服主管" \
  --initial-description "希望整理客訴與客服回覆"
```

See `docs/channel_onboarding_agent.md` for the product rules.
