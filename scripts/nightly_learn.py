#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, time
from collections import defaultdict
from common import root, write_json

FORMAT_HINTS={"太長":"short","簡短":"short","表格":"table","notion":"notion","excel":"excel","圖卡":"visual_card","pdf":"pdf"}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--workspace", required=True); ap.add_argument("--min-evidence", type=int, default=2); args=ap.parse_args()
    r=root(args.workspace); events=[]; p=r/"events/usage_events.jsonl"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip(): events.append(json.loads(line))
    grouped=defaultdict(list)
    for e in events:
        sig=(e.get("correction_signal") or "").lower()
        for k,v in FORMAT_HINTS.items():
            if k.lower() in sig: grouped[(e.get("sender_id"), v)].append(e)
    count=0
    for (uid, pref), evs in grouped.items():
        if len(evs) >= args.min_evidence:
            diff={"target_type":"user_profile","target_id":"discord:"+uid,"operation":"upsert_preference","path":"response_preference.formats","value":pref,"risk_level":"low","confidence":min(0.95,0.55+0.1*len(evs)),"evidence_count":len(evs),"evidence_summary":f"Observed repeated correction/preference for {pref}","source_event_ids":[e["event_id"] for e in evs],"auto_apply":True}
            write_json(r/"diffs/pending"/(f"{int(time.time())}_{uid}_{pref}.json"), diff); count+=1
    print(f"generated_diffs={count}")
if __name__ == "__main__": main()
