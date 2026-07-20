#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, time
from collections import Counter
from common import root

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--workspace", required=True); args=ap.parse_args(); r=root(args.workspace)
    p=r/"events/usage_events.jsonl"; corrections=Counter(); failures=0
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            e=json.loads(line); sig=e.get("correction_signal") or ""
            if sig: corrections[sig]+=1
            if e.get("success_signal") == "failed": failures+=1
    report=r/"reports/repair"/(time.strftime("%Y%m%d")+"_repair.md"); report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("# Self Repair Report\n\n"+f"- repeated_corrections: {corrections.most_common(10)}\n- failed_events: {failures}\n", encoding="utf-8")
    print(report)
if __name__ == "__main__": main()
