"""Generate the synthetic tables that replace the kit's Databricks-only sources.

The Resident 360 kit (stellistic/resident-360-data-workshop) reads daily activity and health
screening from a mirrored Databricks estate. LiveWell has no Databricks (SPEC.md §1), so this
script writes deterministic, synthetic stand-ins next to the vendored kit files:

    content/data/resident360/activity_daily.csv       28 days x 1,500 residents
    content/data/resident360/health_screening.csv     latest (and some earlier) screenings
    content/data/resident360/air_quality_snapshot.csv fixed regional PSI snapshot (kit fallback values)

Design (see ASSUMPTIONS.md, Phase 1):
* Everything is seeded from a hash of resident_id, so re-running produces byte-identical files.
* Step counts correlate with age, engagement and haze. Within the "disengagement pool"
  (no attended events AND at least one dropped programme) a fixed quota per region is given a
  mean below 4,000 steps/day, so gold.resident_360.is_disengaged has a clear, stable regional
  ranking for Mei Lin's question (q_disengaged_regions).
* Rahim (RESIDENT_00061) is generated from content/data/resident360/rahim.json.

Usage:
    python scripts/gen-activity.py            # (re)write the three files
    python scripts/gen-activity.py --check    # exit 1 if the committed files differ from a fresh build
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "data" / "resident360"

ACTIVITY_START = dt.date(2026, 6, 1)
ACTIVITY_DAYS = 28
STEP_GOAL = 7500
DISENGAGED_STEPS_THRESHOLD = 4000

# Fixed regional 24-hour PSI snapshot = the kit's illustrative fallback values
# (API regions west/east/central/north/south mapped to the five HPB regions).
PSI_SNAPSHOT = {"West": 55, "East": 48, "Central": 52, "North": 60, "North-East": 50}
PSI_READING_TS = "2026-06-28T08:00:00+08:00"

# Residents in each region's disengagement pool who get a mean below 4,000 steps/day.
LOW_STEPPER_QUOTA = {"North": 60, "West": 54, "Central": 41, "East": 33, "North-East": 24}

AGE_STEP_FACTOR = {
    "18-29": 1.05, "30-39": 1.0, "40-49": 0.97, "50-59": 0.92, "60-69": 0.84, "70+": 0.72,
}


def seed_for(*parts: str) -> int:
    return int(hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16], 16)


def rng_for(*parts: str) -> random.Random:
    return random.Random(seed_for("livewell-v1", *parts))


def read_csv(name: str) -> list[dict]:
    with open(DATA / name, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_inputs():
    residents = read_csv("residents_reference.csv")
    bookings = read_csv("events_bookings.csv")
    programmes = read_csv("programme_enrolments.csv")
    rahim = json.loads((DATA / "rahim.json").read_text(encoding="utf-8"))
    rid = rahim["resident_id"]
    for r in residents:
        if r["resident_id"] == rid:
            r["region"] = rahim["resident_overrides"]["region"]
            r["planning_area"] = rahim["resident_overrides"]["planning_area"]
            r["age_band"] = rahim["resident_overrides"]["age_band_10y"]
    attended = {b["resident_id"] for b in bookings if b["attended_flag"].strip().upper() == "Y"}
    dropped = {p["resident_id"] for p in programmes if p["status"] == "Dropped"}
    return residents, attended, dropped, rahim


def choose_low_steppers(residents, attended, dropped, rahim_id) -> set[str]:
    pool_by_region: dict[str, list[str]] = {}
    for r in residents:
        rid = r["resident_id"]
        if rid not in attended and rid in dropped:
            pool_by_region.setdefault(r["region"], []).append(rid)
    chosen: set[str] = set()
    for region, pool in pool_by_region.items():
        quota = LOW_STEPPER_QUOTA[region]
        ranked = sorted(pool, key=lambda x: (x != rahim_id, seed_for("low", x)))
        chosen.update(ranked[:quota])
    return chosen


def target_mean_steps(r: dict, low: bool, in_pool: bool, rahim: dict) -> int:
    rid = r["resident_id"]
    if rid == rahim["resident_id"]:
        return int(rahim["activity_targets"]["mean_daily_steps"])
    g = rng_for("steps-base", rid)
    if low:
        return g.randint(2200, 3750)
    if in_pool:
        return g.randint(4300, 6800)
    base = g.lognormvariate(8.78, 0.28)  # median ~6,500
    base *= AGE_STEP_FACTOR.get(r["age_band"], 1.0)
    if PSI_SNAPSHOT[r["region"]] >= 55:
        base *= 0.94
    return int(min(15000, max(4100, base)))


def build_activity(residents, low_steppers, attended, dropped, rahim) -> list[list]:
    rows: list[list] = []
    for r in sorted(residents, key=lambda x: x["resident_id"]):
        rid = r["resident_id"]
        in_pool = rid not in attended and rid in dropped
        target = target_mean_steps(r, rid in low_steppers, in_pool, rahim)
        g = rng_for("steps-daily", rid)
        raw = []
        for d in range(ACTIVITY_DAYS):
            day = ACTIVITY_START + dt.timedelta(days=d)
            weekend = day.weekday() >= 5
            factor = g.uniform(0.55, 1.45) * (1.12 if weekend else 1.0)
            raw.append(factor)
        scale = target * ACTIVITY_DAYS / sum(raw)
        steps = [max(300, round(f * scale)) for f in raw]
        drift = target * ACTIVITY_DAYS - sum(steps)
        steps[-1] = max(300, steps[-1] + drift)
        if rid == rahim["resident_id"]:
            mvpa_mean = rahim["activity_targets"]["mean_mvpa_minutes"]
            sleep_mean = rahim["activity_targets"]["mean_sleep_minutes"]
        else:
            mvpa_mean = max(3.0, target / 10000 * 32 + g.uniform(-4, 4))
            sleep_mean = g.randint(350, 470)
        for d in range(ACTIVITY_DAYS):
            day = ACTIVITY_START + dt.timedelta(days=d)
            s = steps[d]
            mvpa = max(0, round(mvpa_mean * s / target + g.uniform(-3, 3)))
            sleep = max(240, round(sleep_mean + g.uniform(-45, 45)))
            rows.append([rid, day.isoformat(), s, mvpa, sleep, 1 if s >= STEP_GOAL else 0])
    return rows


def risk_band(glucose: float, systolic: int, bmi: float, chol: float) -> str:
    points = 0
    points += glucose >= 6.1
    points += glucose >= 7.0
    points += systolic >= 130
    points += systolic >= 140
    points += bmi >= 25.0
    points += bmi >= 27.5
    points += chol >= 6.2
    if points >= 3:
        return "High"
    if points >= 1:
        return "Moderate"
    return "Low"


def build_screening(residents, low_steppers, rahim) -> list[list]:
    rows: list[list] = []
    age_load = {"18-29": 0.0, "30-39": 0.3, "40-49": 0.6, "50-59": 1.0, "60-69": 1.3, "70+": 1.5}
    for r in sorted(residents, key=lambda x: x["resident_id"]):
        rid = r["resident_id"]
        if rid == rahim["resident_id"]:
            s = rahim["screening"]
            rows.append([rid, "2025-05-20", 25.4, 128, 82, 5.9, 5.2, risk_band(5.9, 128, 25.4, 5.2)])
            rows.append([rid, s["screening_date"], s["bmi"], s["systolic_bp"], s["diastolic_bp"],
                         s["fasting_glucose_mmol"], s["total_cholesterol_mmol"], s["risk_band"]])
            continue
        g = rng_for("screening", rid)
        load = age_load.get(r["age_band"], 0.5) + (0.5 if rid in low_steppers else 0.0)
        if g.random() > 0.55 + 0.1 * load:  # older / less active residents are screened more often
            continue
        n = 2 if g.random() < 0.35 else 1
        for i in range(n):
            year_offset = n - 1 - i
            date = dt.date(2026 - year_offset, g.randint(1, 6), g.randint(1, 28))
            bmi = round(g.gauss(23.2 + 1.3 * load, 3.0), 1)
            sbp = int(g.gauss(118 + 7 * load, 11))
            dbp = int(sbp * g.uniform(0.6, 0.7))
            glu = round(max(4.0, g.gauss(5.1 + 0.45 * load, 0.6)), 1)
            chol = round(max(3.2, g.gauss(4.9 + 0.3 * load, 0.7)), 1)
            rows.append([rid, date.isoformat(), bmi, sbp, dbp, glu, chol, risk_band(glu, sbp, bmi, chol)])
    return rows


def to_csv(header: list[str], rows: list[list]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


def build_all() -> dict[str, str]:
    residents, attended, dropped, rahim = load_inputs()
    low = choose_low_steppers(residents, attended, dropped, rahim["resident_id"])
    activity = build_activity(residents, low, attended, dropped, rahim)
    screening = build_screening(residents, low, rahim)
    air = [[region, psi, PSI_READING_TS, "fixed snapshot (Resident 360 kit illustrative fallback values)"]
           for region, psi in sorted(PSI_SNAPSHOT.items())]
    return {
        "activity_daily.csv": to_csv(
            ["resident_id", "activity_date", "steps", "mvpa_minutes", "sleep_minutes", "goal_met"], activity),
        "health_screening.csv": to_csv(
            ["resident_id", "screening_date", "bmi", "systolic_bp", "diastolic_bp",
             "fasting_glucose_mmol", "total_cholesterol_mmol", "risk_band"], screening),
        "air_quality_snapshot.csv": to_csv(["region", "psi_24h", "reading_ts", "source"], air),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="fail if committed files are stale")
    args = ap.parse_args()
    outputs = build_all()
    stale = []
    for name, text in outputs.items():
        path = DATA / name
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(name)
            continue
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {path.relative_to(ROOT).as_posix()} ({text.count(chr(10)) - 1} rows)")
    if args.check:
        if stale:
            print("STALE: " + ", ".join(stale) + " -- run python scripts/gen-activity.py")
            return 1
        print("OK: generated files are up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
