"""Generate content/data/citizens.json -- the profile tool's data -- from resident_360.

citizens.json is NEVER hand-written (SPEC.md §3.3): it is derived from the same gold build the
Fabric notebook produces (the notebook imports scripts/r360.py), so every profile answer agrees with
the Fabric aggregates. --from-onelake reads the rows the notebook exported from the lakehouse instead. It holds Rahim (RESIDENT_00061) plus a small, deterministic set of demo
personas (one disengaged and one engaged resident per region, plus one unscreened resident).

The get_citizen_profile tool (Lab 3) only ever returns the row of the SESSION resident; the other
personas exist so facilitators can demo "show me another resident's profile" being refused and
so attendees can switch persona in the Builder rail.

Usage:
    python scripts/gen-citizens.py                 # write content/data/citizens.json
    python scripts/gen-citizens.py --check         # exit 1 if the committed file is stale
    python scripts/gen-citizens.py --from-onelake  # build from the loaded lakehouse (Files/export/resident_360.csv)
                                                   # and fail if it differs from the local gold build
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r360  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "content" / "data" / "citizens.json"
REGIONS = ["Central", "East", "North", "North-East", "West"]


def _order(resident_id: str) -> str:
    return hashlib.sha256(f"persona|{resident_id}".encode()).hexdigest()


def conditions(row: dict) -> list[str]:
    out = []
    if row["latest_glucose_mmol"] is not None and row["latest_glucose_mmol"] >= 6.1:
        out.append("elevated blood glucose")
    if row["latest_systolic"] is not None and row["latest_systolic"] >= 140:
        out.append("high blood pressure")
    if row["latest_cholesterol_mmol"] is not None and row["latest_cholesterol_mmol"] >= 6.2:
        out.append("high cholesterol")
    if row["latest_bmi"] is not None and row["latest_bmi"] >= 27.5:
        out.append("high BMI")
    return out


def to_profile(row: dict, programmes: list[dict], persona: dict | None) -> dict:
    return {
        "resident_id": row["resident_id"],
        "display_name": (persona or {}).get("preferred_name"),
        "persona_note": (persona or {}).get("story"),
        "age_band": row["age_band"],
        "gender": row["gender"],
        "region": row["region"],
        "planning_area": row["planning_area"],
        "screening_risk": row["screening_risk"],
        "latest_screening_date": row["latest_screening_date"],
        "conditions": conditions(row),
        "avg_daily_steps": row["avg_daily_steps"],
        "avg_mvpa_min_per_day": row["avg_mvpa_min"],
        "avg_sleep_min": row["avg_sleep_min"],
        "nsc_progress_pct": row["nsc_progress_pct"],
        "programmes": sorted(({"programme_name": p["programme_name"], "status": p["status"]} for p in programmes),
                             key=lambda x: x["programme_name"]),
        "programmes_dropped": row["programmes_dropped"],
        "events_attended": row["events_attended"],
        "events_booked": row["events_booked"],
        "meal_logs": row["meal_logs"],
        "pct_healthier_choice": row["pct_healthier_choice"],
        "healthpoints_balance": row["healthpoints_earned"] - row["healthpoints_redeemed"],
        "region_psi": row["region_psi"],
        "region_is_hazy": row["region_is_hazy"],
        "is_disengaged": row["is_disengaged"],
    }


def _typed(value: str):
    """Undo the CSV export: '' -> None, whole numbers -> int, decimals -> float, else text."""
    if value == "":
        return None
    if value.lstrip("-").isdigit():
        return int(value)
    try:
        return float(value)
    except ValueError:
        return value


def onelake_tables() -> dict:
    """resident_360 + fact_programme_enrolment as exported by load_resident360.ipynb to Files/export/."""
    sys.path.insert(0, str(ROOT / "scripts" / "fabric"))
    import fabriclib as fl  # noqa: PLC0415

    fab = fl.Fabric()
    ws, lh = os.environ.get("FABRIC_WORKSPACE_ID", ""), os.environ.get("FABRIC_LAKEHOUSE_ID", "")
    if not (ws and lh):
        n = fl.names()
        ws = ws or fab.workspace_id(n["fabric_workspace"]) or ""
        lh = lh or (fab.item_id(ws, "Lakehouse", n["lakehouse"]) if ws else "") or ""
    if not (ws and lh):
        raise SystemExit("Fabric workspace / lakehouse not found: run scripts/fabric/deploy.sh")
    out = {}
    for name in ("resident_360", "fact_programme_enrolment"):
        raw = fab.onelake_read(ws, lh, f"Files/export/{name}.csv")
        if raw is None:
            raise SystemExit(f"Files/export/{name}.csv not found: re-run scripts/fabric/deploy.sh --only 20")
        out[name] = [{k: _typed(v) for k, v in row.items()}
                     for row in csv.DictReader(io.StringIO(raw.decode("utf-8")))]
    return out


def build(t: dict | None = None) -> dict:
    t = t or r360.build()
    rahim = r360.load_rahim()
    rows = {r["resident_id"]: r for r in t["resident_360"]}
    progs: dict[str, list[dict]] = {}
    for e in t["fact_programme_enrolment"]:
        progs.setdefault(e["resident_id"], []).append(e)

    chosen = [rahim["resident_id"]]
    candidates = sorted((r for r in rows.values() if r["resident_id"] != rahim["resident_id"]),
                        key=lambda r: _order(r["resident_id"]))
    for region in REGIONS:
        dis = next(r for r in candidates if r["region"] == region and r["is_disengaged"] == 1)
        eng = next(r for r in candidates if r["region"] == region and r["is_disengaged"] == 0
                   and r["events_attended"] >= 2 and r["screening_risk"] != "Not Screened")
        chosen += [dis["resident_id"], eng["resident_id"]]
    unscreened = next(r for r in candidates if r["screening_risk"] == "Not Screened"
                      and r["resident_id"] not in chosen)
    chosen.append(unscreened["resident_id"])

    citizens = [to_profile(rows[rid], progs.get(rid, []), rahim["persona"] if rid == rahim["resident_id"] else None)
                for rid in chosen]
    return {
        "_generated_by": "scripts/gen-citizens.py from the resident_360 gold build (scripts/r360.py)",
        "_do_not_edit": "Regenerate instead: python scripts/gen-citizens.py",
        "_synthetic": "All residents are synthetic. No real person is represented.",
        "default_resident_id": rahim["resident_id"],
        "citizens": citizens,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate citizens.json from resident_360")
    ap.add_argument("--check", action="store_true", help="fail if the committed file is stale")
    ap.add_argument("--from-onelake", action="store_true",
                    help="read resident_360 from the loaded lakehouse (needs az login + deploy.sh)")
    args = ap.parse_args()
    text = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
    if args.from_onelake:
        lake = json.dumps(build(onelake_tables()), indent=2, ensure_ascii=False) + "\n"
        if lake != text:
            print("DIFFERS: citizens built from the lakehouse do not match the local gold build "
                  "(re-run scripts/fabric/deploy.sh --only 20)")
            return 1
        print("OK: citizens built from the lakehouse match the local gold build")
        text = lake
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print("STALE: content/data/citizens.json -- run python scripts/gen-citizens.py")
            return 1
        print("OK: citizens.json is up to date")
        return 0
    OUT.write_text(text, encoding="utf-8", newline="\n")
    n = text.count('"resident_id"')
    print(f"wrote {OUT.relative_to(ROOT).as_posix()} ({n} citizens)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
