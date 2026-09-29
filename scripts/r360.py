"""Minimal LiveWell Resident 360 gold build: the single source of the loader logic.

It rebuilds the minimal LiveWell Resident 360 from the vendored kit files plus the generated
activity/screening/PSI files and Rahim's pinned overlay. The Fabric notebook
content/assets/load_resident360.ipynb uploads this module to Files/livewell/scripts/ and imports it,
so Fabric and the local scripts run the SAME code; the notebook only converts the rows to Delta tables.
It is used by:

* content/assets/load_resident360.ipynb -> the six Delta tables in lh_resident360
* scripts/gen-citizens.py        -> content/data/citizens.json (profile tool)
* scripts/validate-narrative.py  -> data layer + content/fabric/reference-answers.json (Phase 3b)
* scripts/fabric/notebook.py     -> verifies the lakehouse counts against this build

No pandas / Spark needed (stdlib only), so it runs anywhere, including Windows ARM64.

Tables produced (names match the lakehouse lh_resident360):
    resident_360               one row per resident (wide gold)
    dim_region                 one row per region (entity grain for Region)
    dim_programme              one row per programme (entity grain for Programme)
    dim_event_occurrence       one row per event occurrence (entity grain for EventOccurrence)
    fact_event_attendance      attended resident x occurrence pairs only (relationship: attended)
    fact_programme_enrolment   every enrolment row (relationship: enrolledIn)

Usage:
    python scripts/r360.py                 # print table counts, Rahim's row and reference answers
    python scripts/r360.py --out build/r360  # also write every table as CSV (untracked folder)
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "data" / "resident360"

HAZY_PSI = 55
DISENGAGED_STEPS = 4000
DEFAULT_PSI = 50
NSC = "National Steps Challenge"


def _read_csv(name: str) -> list[dict]:
    with open(DATA / name, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _iso(value: str) -> str | None:
    try:
        return dt.date.fromisoformat(value.strip()).isoformat()
    except (ValueError, AttributeError):
        return None


def _int(value) -> int | None:
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def _float(value) -> float | None:
    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return None


def five_year_band(age_band_10y: str, resident_id: str) -> str:
    """Deterministically split the kit's 10-year band into a 5-year band (ASSUMPTIONS.md 1.6)."""
    if age_band_10y == "70+":
        return "70+"
    lo, hi = (int(x) for x in age_band_10y.split("-"))
    upper = int(hashlib.sha256(f"ageband|{resident_id}".encode()).hexdigest(), 16) % 2 == 1
    if lo == 18:
        return "25-29" if upper else "18-24"
    return f"{lo + 5}-{hi}" if upper else f"{lo}-{lo + 4}"


def load_rahim() -> dict:
    return json.loads((DATA / "rahim.json").read_text(encoding="utf-8"))


def build() -> dict[str, list[dict]]:
    rahim = load_rahim()
    rid_rahim = rahim["resident_id"]

    # ---- residents (+ Rahim upsert) -------------------------------------------------------
    residents = []
    for r in _read_csv("residents_reference.csv"):
        row = {
            "resident_id": r["resident_id"],
            "age_band_10y": r["age_band"],
            "age_band": five_year_band(r["age_band"], r["resident_id"]),
            "gender": r["gender"],
            "region": r["region"],
            "planning_area": r["planning_area"],
        }
        if r["resident_id"] == rid_rahim:
            row.update(rahim["resident_overrides"])
        residents.append(row)

    # ---- activity (replaces the Databricks daily_activity table) ---------------------------
    act = defaultdict(lambda: {"steps": 0, "mvpa": 0, "sleep": 0, "goal": 0, "n": 0})
    for a in _read_csv("activity_daily.csv"):
        s = act[a["resident_id"]]
        s["steps"] += int(a["steps"])
        s["mvpa"] += int(a["mvpa_minutes"])
        s["sleep"] += int(a["sleep_minutes"])
        s["goal"] += int(a["goal_met"])
        s["n"] += 1

    # ---- latest screening per resident --------------------------------------------------------
    latest_scr: dict[str, dict] = {}
    for s in _read_csv("health_screening.csv"):
        cur = latest_scr.get(s["resident_id"])
        if cur is None or s["screening_date"] > cur["screening_date"]:
            latest_scr[s["resident_id"]] = s

    # ---- meals (silver: drop invalid dates, cast calories) -----------------------------------
    meals = defaultdict(lambda: {"n": 0, "cal_sum": 0, "cal_n": 0, "healthy": 0})
    for m in _read_csv("meal_logs.csv"):
        if _iso(m["log_date"]) is None:
            continue
        s = meals[m["resident_id"]]
        s["n"] += 1
        cal = _int(m["calories"])
        if cal is not None:
            s["cal_sum"] += cal
            s["cal_n"] += 1
        s["healthy"] += 1 if m["healthier_choice_flag"].strip().upper() == "Y" else 0

    # ---- event bookings (+ Rahim's extra bookings) ---------------------------------------------
    bookings = _read_csv("events_bookings.csv") + [dict(b, resident_id=rid_rahim) for b in rahim["extra_event_bookings"]]
    occurrences: dict[str, dict] = {}
    attended_pairs: dict[tuple[str, str], dict] = {}
    evt = defaultdict(lambda: {"attended": 0, "booked": 0})
    for b in bookings:
        date = _iso(b["event_date"])
        if date is None:
            continue
        occ_id = f"{b['event_id']}|{date}|{b['region']}"
        occurrences.setdefault(occ_id, {
            "event_occurrence_id": occ_id, "event_id": b["event_id"], "event_name": b["event_name"],
            "event_type": b["event_type"], "event_date": date, "region": b["region"],
        })
        e = evt[b["resident_id"]]
        e["booked"] += 1
        if b["attended_flag"].strip().upper() == "Y":
            e["attended"] += 1
            attended_pairs.setdefault((b["resident_id"], occ_id), {
                "resident_id": b["resident_id"], "event_occurrence_id": occ_id,
                "event_id": b["event_id"], "event_date": date, "region": b["region"],
            })

    # ---- programmes --------------------------------------------------------------------------------
    enrolments = []
    prog = defaultdict(lambda: {"enrolled": 0, "dropped": 0})
    for p in _read_csv("programme_enrolments.csv"):
        enrolments.append({
            "resident_id": p["resident_id"], "programme_name": p["programme_name"],
            "enrol_date": _iso(p["enrol_date"]), "status": p["status"], "channel": p["channel"],
        })
        s = prog[p["resident_id"]]
        s["enrolled"] += 1
        s["dropped"] += 1 if p["status"] == "Dropped" else 0

    # ---- rewards / vouchers / challenges -----------------------------------------------------------
    rew = defaultdict(lambda: {"earned": 0, "redeemed": 0})
    for t in json.loads((DATA / "rewards_healthpoints.json").read_text(encoding="utf-8")):
        s = rew[t["resident_id"]]
        s["earned"] += int(t["points_earned"])
        s["redeemed"] += int(t["points_redeemed"])
    vou = defaultdict(lambda: {"n": 0, "value": 0.0})
    for v in _read_csv("evoucher_redemptions.csv"):
        s = vou[v["resident_id"]]
        s["n"] += 1
        s["value"] += _float(v["voucher_value_sgd"]) or 0.0
    cha = defaultdict(lambda: {"active": 0, "prog_sum": 0.0, "n": 0, "nsc": None})
    for c in _read_csv("challenges.csv"):
        s = cha[c["resident_id"]]
        s["active"] += 1 if c["status"] == "Active" else 0
        pct = _float(c["progress_pct"])
        if pct is not None:
            s["prog_sum"] += pct
            s["n"] += 1
            if c["challenge_name"] == NSC:
                s["nsc"] = pct if s["nsc"] is None else max(s["nsc"], pct)

    psi = {r["region"]: int(r["psi_24h"]) for r in _read_csv("air_quality_snapshot.csv")}

    # ---- gold.resident_360 ---------------------------------------------------------------------------
    r360 = []
    for r in residents:
        rid = r["resident_id"]
        a = act.get(rid)
        scr = latest_scr.get(rid)
        m = meals.get(rid)
        e = evt.get(rid, {"attended": 0, "booked": 0})
        p = prog.get(rid, {"enrolled": 0, "dropped": 0})
        w = rew.get(rid, {"earned": 0, "redeemed": 0})
        v = vou.get(rid, {"n": 0, "value": 0.0})
        c = cha.get(rid)
        avg_steps = a["steps"] / a["n"] if a else 0.0
        region_psi = psi.get(r["region"], DEFAULT_PSI)
        row = dict(r)
        row.update({
            "avg_daily_steps": round(avg_steps, 1),
            "avg_mvpa_min": round(a["mvpa"] / a["n"], 1) if a else None,
            "avg_sleep_min": round(a["sleep"] / a["n"], 1) if a else None,
            "days_goal_met": a["goal"] if a else 0,
            "active_days": a["n"] if a else 0,
            "latest_screening_date": scr["screening_date"] if scr else None,
            "latest_bmi": _float(scr["bmi"]) if scr else None,
            "latest_systolic": _int(scr["systolic_bp"]) if scr else None,
            "latest_glucose_mmol": _float(scr["fasting_glucose_mmol"]) if scr else None,
            "latest_cholesterol_mmol": _float(scr["total_cholesterol_mmol"]) if scr else None,
            "screening_risk": scr["risk_band"] if scr else "Not Screened",
            "meal_logs": m["n"] if m else 0,
            "avg_calories": round(m["cal_sum"] / m["cal_n"], 1) if m and m["cal_n"] else None,
            "pct_healthier_choice": round(m["healthy"] / m["n"], 3) if m and m["n"] else None,
            "events_attended": e["attended"],
            "events_booked": e["booked"],
            "programmes_enrolled": p["enrolled"],
            "programmes_dropped": p["dropped"],
            "healthpoints_earned": w["earned"],
            "healthpoints_redeemed": w["redeemed"],
            "vouchers_redeemed": v["n"],
            "voucher_value_sgd": round(v["value"], 2),
            "challenges_active": c["active"] if c else 0,
            "avg_challenge_progress": round(c["prog_sum"] / c["n"], 1) if c and c["n"] else None,
            "nsc_progress_pct": c["nsc"] if c else None,
            "region_psi": region_psi,
            "region_is_hazy": 1 if region_psi >= HAZY_PSI else 0,
            "is_disengaged": 1 if (avg_steps < DISENGAGED_STEPS and e["attended"] < 1 and p["dropped"] > 0) else 0,
        })
        r360.append(row)

    # ---- entity-grain dimensions ---------------------------------------------------------------------
    by_region = defaultdict(list)
    for row in r360:
        by_region[row["region"]].append(row)
    dim_region = [{
        "region": reg,
        "region_psi": rows[0]["region_psi"],
        "region_is_hazy": rows[0]["region_is_hazy"],
        "resident_count": len(rows),
        "disengaged_residents": sum(r["is_disengaged"] for r in rows),
        "disengaged_share_pct": round(100 * sum(r["is_disengaged"] for r in rows) / len(rows), 1),
    } for reg, rows in sorted(by_region.items())]

    disengaged = {row["resident_id"] for row in r360 if row["is_disengaged"] == 1}
    by_prog = defaultdict(lambda: {"residents": set(), "dropped": 0, "first": None})
    for en in enrolments:
        s = by_prog[en["programme_name"]]
        s["residents"].add(en["resident_id"])
        s["dropped"] += 1 if en["status"] == "Dropped" else 0
        if en["enrol_date"] and (s["first"] is None or en["enrol_date"] < s["first"]):
            s["first"] = en["enrol_date"]
    # Gold aggregates on the dims (like resident_count / enrolled_residents) keep officer questions to one row
    # per group: the data agent's ontology query tool returns at most 200 rows (ASSUMPTIONS.md 3b.3).
    dim_programme = [{
        "programme_name": name, "enrolled_residents": len(s["residents"]),
        "dropped_count": s["dropped"], "first_enrolment": s["first"],
        "disengaged_enrolled": len(s["residents"] & disengaged),
    } for name, s in sorted(by_prog.items())]

    return {
        "resident_360": sorted(r360, key=lambda x: x["resident_id"]),
        "dim_region": dim_region,
        "dim_programme": dim_programme,
        "dim_event_occurrence": sorted(occurrences.values(), key=lambda x: x["event_occurrence_id"]),
        "fact_event_attendance": sorted(attended_pairs.values(), key=lambda x: (x["resident_id"], x["event_occurrence_id"])),
        "fact_programme_enrolment": enrolments,
    }


# ---------------------------------------------------------------------------------------------------
# Reference answers for Mei Lin's three questions (content/fabric/question-bank.md)
# ---------------------------------------------------------------------------------------------------

def reference_answers(t: dict[str, list[dict]]) -> dict:
    r360 = {r["resident_id"]: r for r in t["resident_360"]}

    # q_disengaged_regions -- share of disengaged residents by home region
    agg = defaultdict(lambda: [0, 0])
    for r in r360.values():
        agg[r["region"]][0] += 1
        agg[r["region"]][1] += r["is_disengaged"]
    regions = sorted(({"region": k, "residents": n, "disengaged": d, "share_pct": round(100 * d / n, 1)}
                      for k, (n, d) in agg.items()), key=lambda x: (-x["share_pct"], x["region"]))

    # q_dropped_attended_heldin -- residents who dropped a programme and attended >=1 event,
    # counted per region where the attended event occurrence was held (heldIn), distinct residents
    occ_region = {o["event_occurrence_id"]: o["region"] for o in t["dim_event_occurrence"]}
    held = defaultdict(set)
    for f in t["fact_event_attendance"]:
        r = r360.get(f["resident_id"])
        if r and r["programmes_dropped"] >= 1:
            held[occ_region[f["event_occurrence_id"]]].add(f["resident_id"])
    dropped_attended = {f["resident_id"] for f in t["fact_event_attendance"]
                        if r360.get(f["resident_id"], {}).get("programmes_dropped", 0) >= 1}
    heldin = sorted(({"region": k, "residents": len(v)} for k, v in held.items()),
                    key=lambda x: (-x["residents"], x["region"]))

    # q_programmes_disengaged_enrolled -- distinct disengaged residents enrolled per programme
    prog = defaultdict(lambda: {"enrolled": set(), "dropped": set()})
    for en in t["fact_programme_enrolment"]:
        r = r360.get(en["resident_id"])
        if r and r["is_disengaged"] == 1:
            prog[en["programme_name"]]["enrolled"].add(en["resident_id"])
            if en["status"] == "Dropped":
                prog[en["programme_name"]]["dropped"].add(en["resident_id"])
    programmes = sorted(({"programme_name": k, "disengaged_enrolled": len(v["enrolled"]),
                          "disengaged_dropped": len(v["dropped"])} for k, v in prog.items()),
                        key=lambda x: (-x["disengaged_enrolled"], x["programme_name"]))

    total = len(r360)
    disengaged_total = sum(r["is_disengaged"] for r in r360.values())
    return {
        "q_disengaged_regions": {
            "grain": "home region (Resident livesIn Region)",
            "total_residents": total,
            "disengaged_total": disengaged_total,
            "disengaged_share_pct": round(100 * disengaged_total / total, 1),
            "rows": regions,
            "top_region": regions[0]["region"],
            "top_share_pct": regions[0]["share_pct"],
            "second_region": regions[1]["region"],
            "second_share_pct": regions[1]["share_pct"],
            "lowest_region": regions[-1]["region"],
            "lowest_share_pct": regions[-1]["share_pct"],
        },
        "q_dropped_attended_heldin": {
            "grain": "region where the attended event occurrence was held (EventOccurrence heldIn Region)",
            "distinct_residents": len(dropped_attended),
            "rows": heldin,
            "top_region": heldin[0]["region"],
            "top_residents": heldin[0]["residents"],
        },
        "q_programmes_disengaged_enrolled": {
            "grain": "programme (Resident enrolledIn Programme), distinct disengaged residents",
            "rows": programmes,
            "top_programme": programmes[0]["programme_name"],
            "top_disengaged_enrolled": programmes[0]["disengaged_enrolled"],
        },
    }


def rahim_facts(t: dict[str, list[dict]]) -> dict:
    rid = load_rahim()["resident_id"]
    row = next(r for r in t["resident_360"] if r["resident_id"] == rid)
    progs = [e for e in t["fact_programme_enrolment"] if e["resident_id"] == rid]
    return {
        "resident_id": rid,
        "region": row["region"],
        "planning_area": row["planning_area"],
        "age_band": row["age_band"],
        "screening_risk": row["screening_risk"],
        "latest_glucose_mmol": row["latest_glucose_mmol"],
        "avg_daily_steps": row["avg_daily_steps"],
        "avg_mvpa_min": row["avg_mvpa_min"],
        "nsc_progress_pct": row["nsc_progress_pct"],
        "programmes_dropped": row["programmes_dropped"],
        "dropped_programmes": sorted(e["programme_name"] for e in progs if e["status"] == "Dropped"),
        "events_attended": row["events_attended"],
        "events_booked": row["events_booked"],
        "meal_logs": row["meal_logs"],
        "healthpoints_balance": row["healthpoints_earned"] - row["healthpoints_redeemed"],
        "region_psi": row["region_psi"],
        "region_is_hazy": row["region_is_hazy"],
        "is_disengaged": row["is_disengaged"],
    }


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="Local mirror of the Fabric Resident 360 loader")
    ap.add_argument("--out", help="write every table as CSV into this folder (keep it untracked)")
    args = ap.parse_args()
    t = build()
    for name, rows in t.items():
        print(f"{name:26s} {len(rows):>6d} rows")
    print("\nRahim:", json.dumps(rahim_facts(t), indent=2))
    print("\nReference answers:", json.dumps(reference_answers(t), indent=2))
    if args.out:
        out = Path(args.out)
        for name, rows in t.items():
            _write_csv(out / f"{name}.csv", rows)
        print(f"\nwrote CSVs to {out.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
