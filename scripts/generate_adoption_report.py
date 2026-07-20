#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, time
from collections import Counter
from common import root

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--workspace", required=True); args=ap.parse_args(); r=root(args.workspace); c=Counter()
    p=r/"events/usage_events.jsonl"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip(): c[json.loads(line).get("sender_id","unknown")]+=1
    out=r/"reports/adoption"/(time.strftime("%Y%m%d")+"_adoption.md"); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("# Adoption Report\n\n"+"\n".join(f"- {k}: {v}" for k,v in c.most_common()), encoding="utf-8")
    print(out)
if __name__ == "__main__": main()
