#!/usr/bin/env python3
from __future__ import annotations
import argparse, re, time
from pathlib import Path
from common import root

REDACT_PATTERNS = [
    re.compile(r"\b(?:sk|pk|ntn|ghp|github_pat|AIza)[A-Za-z0-9_\-]{12,}\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b\+?\d[\d\s\-()]{7,}\d\b"),
]

def redact(text: str, limit: int = 500) -> str:
    value = str(text or "")[:limit]
    for pattern in REDACT_PATTERNS:
        value = pattern.sub("[REDACTED]", value)
    return value.strip() or "未提供"

def safe_id(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z_-]", "_", str(value or "unknown"))[:120]

def infer_scene(name: str, category: str, description: str) -> tuple[str, float, list[str]]:
    text = f"{name} {category} {description}".lower()
    checks = [
        (("客服", "客訴", "customer", "support"), "客服與客訴處理", 0.72, ["常見問題整理", "客服回覆建議", "客訴原因統計", "FAQ 知識庫"]),
        (("會議", "meeting", "逐字稿", "紀錄"), "會議紀錄與任務追蹤", 0.74, ["會議紀錄", "待辦拆解", "負責人/期限追蹤", "會後摘要"]),
        (("任務", "交辦", "todo", "task", "進度"), "任務交辦與進度稽核", 0.70, ["任務追蹤", "逾期提醒", "卡點整理", "週報"]),
        (("行銷", "marketing", "ig", "threads", "內容"), "行銷內容與成長工作流", 0.68, ["內容排程", "貼文草稿", "成效整理", "素材需求清單"]),
        (("業務", "sales", "客戶", "成交", "報價"), "業務跟進與客戶管理", 0.68, ["跟單提醒", "客戶階段整理", "報價狀態", "成交機率摘要"]),
        (("營運", "ops", "儀表板", "dashboard", "報表"), "營運儀表板與例行回報", 0.66, ["每日摘要", "部門儀表板", "異常提醒", "資料同步"]),
        (("sop", "知識", "第二大腦", "新人", "訓練"), "知識沉澱與新人訓練", 0.66, ["SOP 初稿", "FAQ", "新人訓練路線", "知識庫索引"]),
    ]
    for keys, purpose, conf, menu in checks:
        if any(k in text for k in keys):
            return purpose, conf, menu
    return "尚未確認的部門/專案工作流", 0.35, ["先看範例成果", "整理頻道用途", "建立任務菜單", "我想自己描述"]

def role_lens(role: str, position: str) -> list[str]:
    text = f"{role} {position}".lower()
    if any(k in text for k in ["老闆", "ceo", "owner", "founder"]):
        return ["掌握風險與異常", "看營收/客戶/交付影響", "取得主管摘要", "決定下一步資源配置"]
    if any(k in text for k in ["主管", "manager", "lead", "負責人"]):
        return ["追蹤進度與負責人", "找出重複問題", "整理改善建議", "產出週報/儀表板"]
    if any(k in text for k in ["客服", "業務", "行銷", "執行", "member", "staff"]):
        return ["產生可直接使用的草稿", "查找 FAQ/SOP", "整理回報給主管", "提醒下一步"]
    return ["先用範例成果理解 AI 可協助項目", "用選項排除不需要的方向", "建立第一版任務菜單"]

def build_profile(args) -> str:
    purpose, confidence, scene_menu = infer_scene(args.channel_name, args.channel_category, args.initial_description)
    lens = role_lens(args.creator_role, args.creator_position)
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    combined_menu = [f"{item}（{lens[0]}視角）" if i == 0 else item for i, item in enumerate(scene_menu)]
    return f'''---
schema: channel_profile.v1
platform: discord
surface_type: "{args.surface_type}"
parent_channel_id: "{args.parent_channel_id}"
channel_id: "{args.channel_id}"
channel_name: "{redact(args.channel_name, 120)}"
channel_category: "{redact(args.channel_category, 120)}"
created_by_user_id: "{args.created_by_user_id}"
creator_role: "{redact(args.creator_role, 80)}"
creator_position: "{redact(args.creator_position, 120)}"
inferred_channel_purpose: "{purpose}"
confidence: {confidence:.2f}
last_reviewed_at: "{now}"
---

# Channel Profile

## Purpose hypothesis
- {purpose}
- confidence: {confidence:.2f}
- basis: channel name/category/initial description + creator role/position

## Creator context
- surface_type: {args.surface_type}
- parent_channel_id: {args.parent_channel_id or "none"}
- user_id: {args.created_by_user_id}
- identity / role: {redact(args.creator_role, 80)}
- position: {redact(args.creator_position, 120)}
- permission boundary: {redact(args.permission_boundary, 240)}
- initial description summary: {redact(args.initial_description, 500)}

## Role-aware assistance menu
''' + "".join(f"- {item}\n" for item in combined_menu + lens) + f'''
## Generated artifacts
- 尚未產出

## Accepted / corrected outcomes
- 尚未觀察

## Blocked points
- 尚未觀察

## Recommended next workflow
- 啟動頻道/討論串安裝精靈：先確認角色，再用「我可以協助你哪些問題」選單引導，最後產出第一版可見成果。

## Optimization rule
- Do not ask the user to invent prompts from scratch.
- First infer channel scene from channel name/category.
- Then ask or confirm the creator's role/position.
- Then present role-aware options using: 「依照你的角色，我可以協助你以下問題，你想先從哪個開始？」
- Produce a visible first artifact before asking for deeper structure.

## Do not remember
- 敏感原文
- 一次性個資明細
- secrets / tokens / credentials
'''

def main():
    ap = argparse.ArgumentParser(description="Create or update a channel onboarding profile")
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--channel-id", required=True)
    ap.add_argument("--surface-type", choices=["channel", "thread"], default="channel")
    ap.add_argument("--parent-channel-id", default="")
    ap.add_argument("--channel-name", default="")
    ap.add_argument("--channel-category", default="")
    ap.add_argument("--created-by-user-id", required=True)
    ap.add_argument("--creator-role", default="unknown")
    ap.add_argument("--creator-position", default="unknown")
    ap.add_argument("--permission-boundary", default="unknown")
    ap.add_argument("--initial-description", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dest = root(args.workspace) / "profiles/channels" / f"discord_{safe_id(args.channel_id)}.md"
    content = build_profile(args)
    if args.dry_run:
        print(dest)
        print(content)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    print(f"channel_profile={dest}")

if __name__ == "__main__":
    main()
