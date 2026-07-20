#!/usr/bin/env python3
from __future__ import annotations
import argparse, shutil
from common import root

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--workspace", required=True); ap.add_argument("--snapshot", default="latest"); args=ap.parse_args(); r=root(args.workspace)
    snaps=sorted((r/"history/profiles").glob("*/profiles"))
    if not snaps: raise SystemExit("no snapshots")
    src=snaps[-1] if args.snapshot=="latest" else r/"history/profiles"/args.snapshot/"profiles"
    dest=r/"profiles"
    if dest.exists(): shutil.rmtree(dest)
    shutil.copytree(src,dest)
    print(f"rolled back from {src}")
if __name__ == "__main__": main()
