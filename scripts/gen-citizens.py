"""Generate content/data/citizens.json -- the profile tool's data -- from resident_360.

citizens.json is NEVER hand-written (SPEC.md §3.3): it is derived from the same gold build the
Fabric notebook produces (mirrored locally by scripts/r360.py), so every profile answer agrees with
the Fabric aggregates. It holds Rahim (RESIDENT_00061) plus a small, deterministic set of demo
personas (one disengaged and one engaged resident per region, plus one unscreened resident).

The get_citizen_profile tool (Lab 3) only ever returns the row of the SESSION resident; the other
personas exist so facilitators can demo "show me another resident's profile" being refused and
so attendees can switch persona in the Builder rail.

Usage:
    python scripts/gen-citizens.py           # write content/data/citizens.json
    python scripts/gen-citizens.py --check   # exit 1 if the committed file is stale
"""

from __future__ import annotations

import argparse
import hashlib
import json
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


def build() -> dict:
    t = r360.build()
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
    args = ap.parse_args()
    text = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
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
