#!/usr/bin/env python3
from __future__ import annotations
import argparse, shutil, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

def run(cmd, dry=False):
    print("$", " ".join(map(str, cmd)))
    if not dry:
        subprocess.run(list(map(str, cmd)), check=True)

def main():
    ap=argparse.ArgumentParser(description="Install automatic hooks/cron for company-adaptive-openclaw")
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--install-hooks", action="store_true")
    ap.add_argument("--enable-hooks", action="store_true")
    ap.add_argument("--install-cron", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args=ap.parse_args()
    workspace=Path(args.workspace).expanduser().resolve()
    if args.install_hooks or args.enable_hooks:
        hooks_dir=workspace/"hooks"
        for name in ["company-adaptive-logger", "company-adaptive-bootstrap"]:
            src=REPO/"hooks"/name; dest=hooks_dir/name
            print(f"copy {src} -> {dest}")
            if not args.dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists(): shutil.rmtree(dest)
                shutil.copytree(src, dest)
    if args.enable_hooks:
        run(["openclaw", "hooks", "enable", "company-adaptive-logger"], args.dry_run)
        run(["openclaw", "hooks", "enable", "company-adaptive-bootstrap"], args.dry_run)
        print("NOTE: restart OpenClaw gateway for newly enabled hooks to load if they were not already discovered.")
    if args.install_cron:
        cron=workspace/"adaptive-openclaw"/"cron"
        if not args.dry_run: cron.mkdir(parents=True, exist_ok=True)
        runner=cron/"nightly_company_adaptive.sh"
        content=f'''#!/usr/bin/env bash\nset -euo pipefail\ncd "{REPO}"\npython3 scripts/nightly_learn.py --workspace "{workspace}"\npython3 scripts/self_repair_check.py --workspace "{workspace}"\npython3 scripts/generate_adoption_report.py --workspace "{workspace}"\nif compgen -G "{workspace}/adaptive-openclaw/diffs/pending/*.json" > /dev/null; then\n  python3 scripts/apply_profile_diff.py --workspace "{workspace}" "{workspace}"/adaptive-openclaw/diffs/pending/*.json\nfi\npython3 scripts/validate_profiles.py --workspace "{workspace}"\n'''
        print(f"write {runner}")
        if not args.dry_run:
            runner.write_text(content, encoding="utf-8"); runner.chmod(0o755)
        print("Cron runner created. Register it with your scheduler after reviewing it.")
    if not (args.install_hooks or args.enable_hooks or args.install_cron):
        print("Nothing selected. Use --install-hooks, --enable-hooks, and/or --install-cron.")
if __name__ == "__main__": main()
