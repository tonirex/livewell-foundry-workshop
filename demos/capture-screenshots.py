#!/usr/bin/env python3
"""Capture the 🟢 Navigator screenshot slots of content/labs/lab-0*-portal.md from the live portal.

    python demos/capture-screenshots.py --list-missing        # which slots have no PNG yet (no browser)
    python demos/capture-screenshots.py                        # capture every slot a script can take (~30 min)
    python demos/capture-screenshots.py --only lab-01          # one lab
    python demos/capture-screenshots.py --only lab-03/12 lab-03/13
    python demos/capture-screenshots.py --link                 # turn filled slots into markdown images

Prerequisites: `python demos/portal.py login` once (facilitator account), and the demo agents from
`python demos/create-demo-agents.py`. Scenes chat with the livewell-demo-* agents and the hosted agent, open
menus and dialogs and cancel them; nothing is saved. Tenant/subscription IDs, endpoints and e-mails are
rewritten in the page and the account button is masked before each shot. Review every PNG before committing.
PNGs go to content/labs/screenshots/lab-0N/. The four slots that need a participant lab account are listed as
manual (see scenes.MANUAL).
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import portal as P  # noqa: E402
import scenes as S  # noqa: E402


def status_rows(results: dict[str, str] | None = None) -> list[tuple[str, str, str]]:
    rows = []
    for sid, slot in sorted(S.slots().items()):
        if results and sid in results:
            state = results[sid]
        elif sid in S.MANUAL:
            state = "manual: " + S.MANUAL[sid]
        elif slot.file.exists():
            state = "present"
        else:
            state = "missing"
        rows.append((sid, slot.path, state))
    return rows


def link(dry_run: bool = False) -> int:
    """Rewrite every slot whose PNG exists as `![caption](path)`; slots without a PNG stay as slots."""
    changed = 0
    for md in sorted(S.LABS.glob("lab-0*-portal.md")):
        lines = md.read_text(encoding="utf-8").split("\n")
        out = []
        for line in lines:
            m = S.SLOT_RE.match(line)
            if m and (S.LABS / m["path"]).exists():
                line = f"{m['indent']}![{m['caption']}]({m['path']})"
                changed += 1
            out.append(line)
        if not dry_run:
            md.write_text("\n".join(out), encoding="utf-8")
    print(f"[capture] linked {changed} slot(s){' (dry run)' if dry_run else ''}")
    return changed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", nargs="*", metavar="SLOT", help="lab-0N or lab-0N/NN (several allowed)")
    ap.add_argument("--list-missing", action="store_true", help="print the slots without a PNG and exit")
    ap.add_argument("--link", action="store_true", help="convert filled slots into markdown images and exit")
    ap.add_argument("--dry-run", action="store_true", help="with --link: count only")
    ap.add_argument("--missing-only", action="store_true", help="capture only slots that have no PNG yet")
    ap.add_argument("--headless", action="store_true", help="no browser window (the default is headed Edge)")
    args = ap.parse_args()

    if args.link:
        link(args.dry_run)
        return 0
    if args.list_missing:
        rows = [r for r in status_rows() if r[2] != "present"]
        for sid, path, state in rows:
            print(f"{sid:10} {state:60} {path}")
        print(f"[capture] {len(rows)} of {len(S.slots())} slots have no PNG")
        return 0

    only = set(args.only) if args.only else None
    if args.missing_only:
        missing = {sid for sid, _, state in status_rows() if state == "missing"}
        only = (only & missing) if only else missing
    wanted = [name for name, (_, ids) in S.SCENES.items()
              if only is None or any(sid in only or sid.split("/")[0] in only for sid in ids)]
    if not wanted:
        print("[capture] nothing to capture")
        return 0

    from playwright.sync_api import sync_playwright

    started = time.time()
    with sync_playwright() as pw:
        ctx, page = P.open_portal(pw, headless=args.headless)
        run = S.Run(page, mode="shots", only=only, log=lambda m: print(m, flush=True))
        for name in wanted:
            fn, ids = S.SCENES[name]
            print(f"[capture] scene {name}", flush=True)
            with run.soft(f"scene {name}", *ids):
                fn(run)
        ctx.close()

    selected = [sid for sid in S.slots() if run.selected(sid)]
    for sid in selected:
        if sid not in run.results:
            run.results[sid] = "manual: " + S.MANUAL[sid] if sid in S.MANUAL else "not captured"
    print(f"\n| Slot | File | Result |\n|---|---|---|")
    for sid, path, state in status_rows(run.results):
        if sid in selected:
            print(f"| {sid} | `{path}` | {state} |")
    ok = sum(1 for sid in selected if run.results[sid].startswith("captured"))
    print(f"\n[capture] {ok}/{len(selected)} captured in {(time.time() - started) / 60:.1f} min - review the PNGs, "
          "then run with --link")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
