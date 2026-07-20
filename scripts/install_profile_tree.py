#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from common import root

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"

def render(text: str, **kw):
    for k, v in kw.items():
        text = text.replace("{{"+k+"}}", str(v))
    return text

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--mode", choices=["solo_team", "client_standard"], default="solo_team")
    ap.add_argument("--company-name", default="TBD")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    r = root(args.workspace)
    files = {
        r/"config.yaml": f"mode: {args.mode}\ncompany_name: {args.company_name}\nrls_enabled: {str(args.mode=='client_standard').lower()}\n",
        r/"profiles/company.md": render((TEMPLATES/"company_profile.md").read_text(), company_name=args.company_name, mode=args.mode, rls_enabled=str(args.mode=="client_standard").lower(), permission_model=("RLS enabled; deny cross-department sensitive by default." if args.mode=="client_standard" else "RLS disabled; small-team trust model, but sensitive raw details still forbidden.")),
        r/"profiles/departments/_template.md": (TEMPLATES/"department_profile.md").read_text(),
        r/"profiles/users/_template.md": (TEMPLATES/"user_profile.md").read_text(),
        r/"profiles/workflows/_template.md": (TEMPLATES/"workflow_profile.md").read_text(),
        r/"events/usage_events.jsonl": "",
        r/"diffs/pending/.keep": "",
        r/"diffs/applied/.keep": "",
        r/"diffs/rejected/.keep": "",
        r/"reports/adoption/.keep": "",
        r/"reports/repair/.keep": "",
    }
    if args.dry_run:
        for p in files: print(p)
        return
    for p, content in files.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists(): p.write_text(content, encoding="utf-8")
    print(f"installed {r}")
if __name__ == "__main__": main()
