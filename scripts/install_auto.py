#!/usr/bin/env python3
from __future__ import annotations
import argparse, shutil, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def run(cmd, dry: bool = False, tolerate_fail: bool = False):
    print("$", " ".join(map(str, cmd)))
    if dry:
        return
    result = subprocess.run(list(map(str, cmd)), text=True, capture_output=True)
    if result.returncode != 0 and not tolerate_fail:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        raise SystemExit(result.returncode)


def write_runner(workspace: Path, dry: bool) -> Path:
    cron = workspace / "adaptive-openclaw" / "cron"
    if not dry:
        cron.mkdir(parents=True, exist_ok=True)
    runner = cron / "nightly_company_adaptive.sh"
    content = f'''#!/usr/bin/env bash
set -euo pipefail
cd "{REPO}"
python3 scripts/nightly_learn.py --workspace "{workspace}"
python3 scripts/self_repair_check.py --workspace "{workspace}"
python3 scripts/generate_adoption_report.py --workspace "{workspace}"
if compgen -G "{workspace}/adaptive-openclaw/diffs/pending/*.json" > /dev/null; then
  python3 scripts/apply_profile_diff.py --workspace "{workspace}" "{workspace}"/adaptive-openclaw/diffs/pending/*.json
fi
python3 scripts/validate_profiles.py --workspace "{workspace}"
'''
    print(f"write {runner}")
    if not dry:
        runner.write_text(content, encoding="utf-8")
        runner.chmod(0o755)
    return runner


def install_launchd(workspace: Path, runner: Path, hour: int, minute: int, dry: bool):
    label = "ai.openclaw.company-adaptive.nightly"
    plist = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
    plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{label}</string>
  <key>ProgramArguments</key><array><string>{runner}</string></array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>{hour}</integer><key>Minute</key><integer>{minute}</integer></dict>
  <key>StandardOutPath</key><string>{workspace}/adaptive-openclaw/cron/nightly.out.log</string>
  <key>StandardErrorPath</key><string>{workspace}/adaptive-openclaw/cron/nightly.err.log</string>
</dict>
</plist>
'''
    print(f"write {plist}")
    if not dry:
        plist.parent.mkdir(parents=True, exist_ok=True)
        plist.write_text(plist_content, encoding="utf-8")
    run(["launchctl", "unload", str(plist)], dry=dry, tolerate_fail=True)
    run(["launchctl", "load", str(plist)], dry=dry)


def main():
    ap = argparse.ArgumentParser(description="Install automatic hooks/cron for company-adaptive-openclaw")
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--install-hooks", action="store_true")
    ap.add_argument("--enable-hooks", action="store_true", help="Enable safe default hooks: logger only")
    ap.add_argument("--enable-bootstrap", action="store_true", help="Experimental: enable runtime bootstrap profile injection")
    ap.add_argument("--install-cron", action="store_true", help="Create nightly runner script")
    ap.add_argument("--enable-cron", action="store_true", help="Register nightly scheduler after creating runner")
    ap.add_argument("--hour", type=int, default=3)
    ap.add_argument("--minute", type=int, default=20)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    workspace = Path(args.workspace).expanduser().resolve()

    if args.install_hooks or args.enable_hooks or args.enable_bootstrap:
        hooks_dir = workspace / "hooks"
        for name in ["company-adaptive-logger", "company-adaptive-bootstrap"]:
            src = REPO / "hooks" / name
            dest = hooks_dir / name
            print(f"copy {src} -> {dest}")
            if not args.dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(src, dest)

    if args.enable_hooks:
        run(["openclaw", "hooks", "enable", "company-adaptive-logger"], args.dry_run)
        print("Safe default enabled: company-adaptive-logger only.")
        print("Bootstrap runtime injection remains disabled unless --enable-bootstrap is explicitly passed.")
        print("NOTE: restart OpenClaw gateway once for newly discovered hooks to load.")

    if args.enable_bootstrap:
        run(["openclaw", "hooks", "enable", "company-adaptive-bootstrap"], args.dry_run)
        print("EXPERIMENTAL bootstrap hook enabled. Use only after customer approval and canary testing.")
        print("NOTE: restart OpenClaw gateway once for newly discovered hooks to load.")

    if args.install_cron or args.enable_cron:
        runner = write_runner(workspace, args.dry_run)
        if args.enable_cron:
            if sys.platform == "darwin":
                install_launchd(workspace, runner, args.hour, args.minute, args.dry_run)
            else:
                print("Non-macOS scheduler registration is not automatic yet. Add runner to crontab manually.")

    if not (args.install_hooks or args.enable_hooks or args.enable_bootstrap or args.install_cron or args.enable_cron):
        print("Nothing selected. Use --install-hooks, --enable-hooks, --enable-bootstrap, --install-cron, and/or --enable-cron.")


if __name__ == "__main__":
    main()
