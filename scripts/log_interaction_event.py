#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, time, uuid
from common import root

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--workspace", required=True); ap.add_argument("--sender-id", required=True); ap.add_argument("--channel-id", required=True); ap.add_argument("--task-type", default="unknown"); ap.add_argument("--correction-signal", default=""); ap.add_argument("--success-signal", default=""); ap.add_argument("--artifact-delivered", action="store_true"); args=ap.parse_args()
    evt={"event_id":"evt_"+uuid.uuid4().hex[:12],"timestamp":time.strftime("%Y-%m-%dT%H:%M:%S%z"),"platform":"discord","sender_id":args.sender_id,"channel_id":args.channel_id,"task_type":args.task_type,"correction_signal":args.correction_signal,"success_signal":args.success_signal,"artifact_delivered":bool(args.artifact_delivered)}
    p=root(args.workspace)/"events/usage_events.jsonl"; p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f: f.write(json.dumps(evt, ensure_ascii=False)+"\n")
    print(evt["event_id"])
if __name__ == "__main__": main()
