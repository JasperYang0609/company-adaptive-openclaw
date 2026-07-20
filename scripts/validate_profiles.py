#!/usr/bin/env python3
from __future__ import annotations
import argparse, sys
from pathlib import Path
from common import root

REQUIRED = [
    "config.yaml",
    "profiles/company.md",
    "profiles/departments/_template.md",
    "profiles/users/_template.md",
    "profiles/workflows/_template.md",
    "events/usage_events.jsonl",
]

def has_frontmatter(p: Path) -> bool:
    text = p.read_text(encoding="utf-8")
    return text.startswith("---\n") and "\n---\n" in text[4:]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workspace", required=True); args=ap.parse_args()
    r = root(args.workspace)
    errors=[]
    for rel in REQUIRED:
        if not (r/rel).exists(): errors.append(f"missing {rel}")
    for p in (r/"profiles").glob("**/*.md") if (r/"profiles").exists() else []:
        if not has_frontmatter(p): errors.append(f"missing frontmatter {p}")
    if errors:
        print("INVALID")
        for e in errors: print("-", e)
        sys.exit(1)
    print("VALID", r)
if __name__ == "__main__": main()
