#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, time
from collections import Counter, defaultdict
from common import root, write_json

FORMAT_HINTS={"太長":"short","簡短":"short","表格":"table","notion":"notion","excel":"excel","圖卡":"visual_card","pdf":"pdf"}
CHANNEL_WORKFLOW_HINTS={
    "meeting_notes":"AI 會議秘書長",
    "notion_or_database":"部門資料/Notion 工作流",
    "spreadsheet_or_report":"部門儀表板與例行報表",
    "visual_artifact":"行銷內容/視覺素材工作流",
    "development":"開發/技術任務工作流",
    "general":"頻道安裝精靈：先產出可見成果再修正",
}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--workspace", required=True); ap.add_argument("--min-evidence", type=int, default=2); args=ap.parse_args()
    r=root(args.workspace); events=[]; p=r/"events/usage_events.jsonl"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip(): events.append(json.loads(line))
    grouped=defaultdict(list)
    channel_grouped=defaultdict(list)
    for e in events:
        sig=(e.get("correction_signal") or "").lower()
        for k,v in FORMAT_HINTS.items():
            if k.lower() in sig: grouped[(e.get("sender_id"), v)].append(e)
        cid=str(e.get("channel_id") or "")
        if cid and cid != "unknown" and e.get("sender_id") != "assistant":
            channel_grouped[cid].append(e)
    count=0
    now=int(time.time())
    for (uid, pref), evs in grouped.items():
        if uid and uid != "unknown" and len(evs) >= args.min_evidence:
            diff={"target_type":"user_profile","target_id":"discord:"+uid,"operation":"upsert_preference","path":"response_preference.formats","value":pref,"risk_level":"low","confidence":min(0.95,0.55+0.1*len(evs)),"evidence_count":len(evs),"evidence_summary":f"Observed repeated correction/preference for {pref}","source_event_ids":[e["event_id"] for e in evs],"auto_apply":True}
            write_json(r/"diffs/pending"/(f"{now}_{uid}_{pref}.json"), diff); count+=1
    for cid, evs in channel_grouped.items():
        if len(evs) >= args.min_evidence:
            tasks=[e.get("task_type") or "general" for e in evs]
            most_common=Counter(tasks).most_common(2)
            workflows=[CHANNEL_WORKFLOW_HINTS.get(t, "頻道安裝精靈：先產出可見成果再修正") for t,_ in most_common]
            value=" / ".join(dict.fromkeys(workflows))
            diff={"target_type":"channel_profile","target_id":"discord:"+cid,"operation":"append_repair_note","path":"recommended_next_workflow","value":value,"risk_level":"low","confidence":min(0.9,0.50+0.08*len(evs)),"evidence_count":len(evs),"evidence_summary":f"Observed channel usage patterns: {', '.join(f'{t}={n}' for t,n in most_common)}","source_event_ids":[e["event_id"] for e in evs if e.get("event_id")],"auto_apply":True}
            write_json(r/"diffs/pending"/(f"{now}_channel_{cid}.json"), diff); count+=1
    print(f"generated_diffs={count}")
if __name__ == "__main__": main()
