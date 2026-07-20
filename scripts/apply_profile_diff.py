#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, shutil, time
from pathlib import Path
from common import root, read_json, is_forbidden_diff, snapshot

def target_path(r: Path, diff: dict) -> Path:
    tid=diff["target_id"].replace(":","_").replace("/","_")
    if diff["target_type"]=="user_profile": return r/"profiles/users"/(tid+".md")
    if diff["target_type"]=="department_profile": return r/"profiles/departments"/(tid+".md")
    if diff["target_type"]=="workflow_profile": return r/"profiles/workflows"/(tid+".md")
    return r/"profiles/company.md"

def append_rule(path: Path, diff: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists(): path.write_text("---\nschema: generated_profile.v1\n---\n\n# Generated Profile\n", encoding="utf-8")
    text=path.read_text(encoding="utf-8")
    block=f"\n\n## Auto-applied rule {time.strftime('%Y-%m-%d')}\n- path: `{diff['path']}`\n- value: `{diff['value']}`\n- confidence: {diff['confidence']}\n- evidence_count: {diff['evidence_count']}\n- summary: {diff['evidence_summary']}\n"
    path.write_text(text+block, encoding="utf-8")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--workspace", required=True); ap.add_argument("diff", nargs="+"); args=ap.parse_args()
    r=root(args.workspace); applied=0; rejected=0
    for d in args.diff:
        p=Path(d); diff=read_json(p)
        if is_forbidden_diff(diff) or not diff.get("auto_apply"):
            dest=r/"diffs/rejected"/p.name; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p,dest); rejected+=1; continue
        snapshot(args.workspace)
        append_rule(target_path(r,diff), diff)
        dest=r/"diffs/applied"/p.name; dest.parent.mkdir(parents=True, exist_ok=True); shutil.move(str(p), dest); applied+=1
    print(f"applied={applied} rejected={rejected}")
if __name__ == "__main__": main()
