#!/usr/bin/env python3
"""The narrative <-> Fabric data agent gate (SPEC.md §11.1, Phase 3b). Run it on every redeploy and dry run.

Layers (--layers static,data,live or all; default static,data):

  static  Every beat in content/narrative/rahim.md has a seat and a source; citizen beats never use Fabric;
          every fabric beat -> test-prompts.json prompt -> question-bank.md question (verbatim text, reference
          link, strict/advisory gate, no orphans, at most 3); glossary definitions verbatim in the coach and
          data-agent instructions, and no spelling drift; no resident_id in officer prompts, the question bank,
          fabric beats or the reference answers; no hard-coded numbers in beats; every {{ref:...}} value filled
          and equal to the current reference.
  data    Rebuilds Resident 360 with scripts/r360.py (the module the Fabric notebook imports): joins, region
          and programme names, the glossary rules on every row, Rahim's row against citizens.json, the intake
          documents and the story; then writes content/fabric/reference-answers.json.
  live    Asks the published Fabric data agent each question-bank question --runs times (default 3) with
          your Azure CLI token: no resident_id, grouped, exact counts, order within +-1 rank of the reference,
          latency logged (expect 30-90 s, flag > 120 s). "strict" questions fail the gate; "advisory" ones only
          warn. The coach-routing row (the LiveWell agent calls Fabric IQ for Mei and never for Rahim) is read
          from the latest Lab 3 Builder run with the Fabric step (content/assets/.runs/lab3-*.json, written by
          `make -C content/assets validate-rail`); SKIP when there is none.

  python scripts/validate-narrative.py                           # static + data, offline, a few seconds
  python scripts/validate-narrative.py --fill                    # fill or refresh {{ref:...}} values first
  python scripts/validate-narrative.py --layers all --env mcaps  # + live: 3 questions x 3 runs, about 5 min

--fill turns each {{ref:key}} in rahim.md and content/labs/*.md into <!--ref:key-->value<!--/ref-->: the value
renders, and a later --fill refreshes it. Values come only from the reference answers, never from a portal run.
The report demos/NARRATIVE-VALIDATION-<date>.md is written when the live layer runs (or with --report).
Exit code 1 on any FAIL; WARN and SKIP do not fail the gate. --check (CI) never writes reference-answers.json,
so an out-of-date file is a FAIL.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import r360  # noqa: E402
import wsconfig  # noqa: E402

_spec = importlib.util.spec_from_file_location("check_content", ROOT / "scripts" / "check-content.py")
cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cc)

NARRATIVE = ROOT / "content" / "narrative" / "rahim.md"
QBANK = ROOT / "content" / "fabric" / "question-bank.md"
REF_JSON = ROOT / "content" / "fabric" / "reference-answers.json"
PROMPTS = ROOT / "content" / "prompts" / "test-prompts.json"
GLOSSARY = ROOT / "content" / "config" / "glossary.yaml"
COACH = ROOT / "content" / "prompts" / "coach-instructions.md"
AGENT_INSTRUCTIONS = ROOT / "content" / "fabric" / "data-agent-instructions.md"
CITIZENS = ROOT / "content" / "data" / "citizens.json"
INTAKE = ROOT / "content" / "data" / "intake"
DEMOS = ROOT / "demos"

PLACEHOLDER_RE = re.compile(r"\{\{ref:([A-Za-z0-9_.]+)\}\}")
FILLED_RE = re.compile(r"<!--ref:([A-Za-z0-9_.]+)-->(.*?)<!--/ref-->")
RESIDENT_ID_RE = re.compile(r"RESIDENT_\d+", re.IGNORECASE)
QBANK_ROW_RE = re.compile(r"^\|\s*`(q_[a-z0-9_]+)`\s*\|\s*([^|]+?)\s*\|\s*`([a-z0-9_]+)`\s*\|(.*)$", re.MULTILINE)
NUMBER_RE = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")
PERCENT_RE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*%")
# Digits that are names, not data: lab and chapter numbers, Resident 360, Healthy 365, the 995 emergency line.
ALLOWED_DIGITS_RE = re.compile(r"\b(?:Lab|lab|Chapter|chapter)\s+\d\b|\bResident 360\b|\bHealthy 365\b|\b995\b")
LAYERS = ("static", "data", "live")
SLOW_S = 120
# Per question: which reference rows the answer is grouped by, the count that must match exactly, and an
# optional total that must appear in the answer.
LIVE_SHAPE = {
    "q_disengaged_regions": ("region", "disengaged", None),
    "q_programmes_disengaged_enrolled": ("programme_name", "disengaged_enrolled", None),
    "q_dropped_attended_heldin": ("region", "residents", "distinct_residents"),
}
GQL_RE = re.compile(r"^```gql name=([a-z0-9_.]+)\n(.*?)^```\s*$", re.MULTILINE | re.DOTALL)


def canonical_gql() -> dict[str, str]:
    """Canonical GQL per question (and per total, e.g. q_dropped_attended_heldin.distinct_residents)."""
    return {m.group(1): m.group(2).strip() for m in GQL_RE.finditer(QBANK.read_text(encoding="utf-8"))}


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def fill_files() -> list[Path]:
    return [NARRATIVE] + sorted((ROOT / "content" / "labs").glob("*.md"))


class Gate:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, layer: str, name: str, status: str, details: list[str] | None = None) -> None:
        details = list(details or [])
        self.rows.append({"layer": layer, "check": name, "status": status, "details": details})
        print(f"{status:<4}  [{layer}] {name}", flush=True)
        for d in details[:25]:
            print(f"        - {d}")
        if len(details) > 25:
            print(f"        ... {len(details) - 25} more")

    def check(self, layer: str, name: str, problems: list[str], advisory: bool = False) -> None:
        self.add(layer, name, ("WARN" if advisory else "FAIL") if problems else "PASS", problems)

    def count(self, status: str) -> int:
        return sum(1 for r in self.rows if r["status"] == status)


# ---------------------------------------------------------------------------------------------------
# Reference answers and --fill
# ---------------------------------------------------------------------------------------------------

def reference(t: dict) -> dict:
    rahim = r360.rahim_facts(t)
    rahim.pop("resident_id", None)  # expected answers never carry a resident_id
    return {
        "_generated_by": "scripts/validate-narrative.py (data layer) from the scripts/r360.py gold build",
        "_do_not_edit": "Regenerate: python scripts/validate-narrative.py --layers data",
        "_synthetic": "Aggregates over synthetic residents. Quote these numbers, never numbers from a portal run.",
        "rahim": rahim,
        **r360.reference_answers(t),
    }


def lookup(ref: dict, key: str):
    cur = ref
    for part in key.split("."):
        if isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        elif isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise KeyError(key)
    if isinstance(cur, (dict, list)):
        raise KeyError(f"{key} is not a single value")
    return cur


def fmt(key: str, value) -> str:
    """Rounded display value: shares and mmol/L to one decimal, whole numbers with thousands separators."""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        if key.endswith(("_pct", "_mmol")) or not value.is_integer():
            return f"{value:,.1f}"
        return f"{int(value):,}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def fill(ref: dict) -> list[str]:
    def repl(m: re.Match) -> str:
        try:
            value = fmt(m.group(1), lookup(ref, m.group(1)))
        except KeyError:
            return m.group(0)  # left as is; the static layer reports the unknown key
        return f"<!--ref:{m.group(1)}-->{value}<!--/ref-->"

    changed = []
    for path in fill_files():
        raw = path.read_bytes().decode("utf-8")
        new = FILLED_RE.sub(repl, PLACEHOLDER_RE.sub(repl, raw))
        if new != raw:
            path.write_bytes(new.encode("utf-8"))
            changed.append(rel(path))
    return changed


# ---------------------------------------------------------------------------------------------------
# Static layer
# ---------------------------------------------------------------------------------------------------

def parse_beats(md: str) -> list[dict]:
    body = cc.strip_code(md)
    marks = list(cc.BEAT_RE.finditer(body))
    beats = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        heading = re.search(r"^#{1,6} ", body[m.end():end], flags=re.MULTILINE)
        if heading:
            end = m.end() + heading.start()
        beat, seat, source, pid = m.groups()
        beats.append({"beat": beat, "seat": seat, "source": source, "prompt": pid, "text": body[m.end():end]})
    return beats


def parse_qbank() -> dict[str, dict]:
    rows = {}
    for m in QBANK_ROW_RE.finditer(QBANK.read_text(encoding="utf-8")):
        rest = m.group(4)
        gate = "advisory" if "advisory" in rest else "strict" if "strict" in rest else "?"
        rows[m.group(1)] = {"question": m.group(2).strip(), "prompt": m.group(3), "gate": gate}
    return rows


def spelling_rules(glossary: dict) -> list[tuple[str, re.Pattern, bool]]:
    """(canonical, pattern, exact). exact=False: multi-word term, drift = different separators
    ("North East", "e-Vouchers"); exact=True: an `avoid` spelling from glossary.yaml."""
    rules = []
    avoid = {t["term"]: t.get("avoid", []) for t in glossary.get("terms", [])}
    canon = ([t["term"] for t in glossary.get("terms", [])] + glossary.get("regions", [])
             + glossary.get("programmes", []) + glossary.get("challenges", []))
    for term in canon:
        core = re.sub(r"\s*\([^)]*\)$", "", term)
        parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", core)
        if len(parts) >= 2:
            pat = r"(?<![\w-])" + r"[ \t-]*".join(map(re.escape, parts)) + r"(?![\w-])"
            rules.append((core, re.compile(pat, re.IGNORECASE), False))
        for bad in avoid.get(term, []):
            rules.append((term, re.compile(r"(?<![\w-])" + re.escape(bad) + r"(?![\w-])"), True))
    return rules


def _skeleton(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[A-Za-z0-9]", "", s))


def ontology_identifiers() -> set[str]:
    """Entity and relationship type ids (EventOccurrence, heldIn, ...) are identifiers, not prose spellings."""
    bp = yaml.safe_load((ROOT / "content" / "fabric" / "ontology.blueprint.yaml").read_text(encoding="utf-8"))
    return {x["id"] for key in ("entity_types", "relationship_types") for x in bp.get(key, []) if x.get("id")}


def static_layer(g: Gate, ref: dict, prompts: dict, glossary: dict, qrows: dict) -> None:
    L = "static"
    md = NARRATIVE.read_text(encoding="utf-8")
    beats = parse_beats(md)
    body = cc.strip_code(md)

    # 1. every beat tagged with seat + source
    problems = []
    loose = re.findall(r"\*\*\[ch\d+\.\d+[^\]]*\]\*\*", body)
    if not beats:
        problems.append("no beat tags in rahim.md")
    if len(loose) != len(beats):
        problems.append(f"{len(loose) - len(beats)} beat tag(s) without a valid seat/source/prompt")
    ids = [b["beat"] for b in beats]
    problems += [f"duplicate beat id {b}" for b in sorted({b for b in ids if ids.count(b) > 1})]
    for b in beats:
        if b["prompt"] not in prompts:
            problems.append(f"{b['beat']}: unknown prompt {b['prompt']}")
        elif prompts[b["prompt"]].get("seat") != b["seat"]:
            problems.append(f"{b['beat']}: seat {b['seat']}, but prompt {b['prompt']} is {prompts[b['prompt']].get('seat')}")
    g.check(L, f"every beat has a seat, a source and a known prompt ({len(beats)} beats)", problems)

    # 2. citizen beats never Fabric; officer beats always Fabric
    problems = []
    for b in beats:
        if b["seat"] == "citizen" and b["source"] == "fabric":
            problems.append(f"{b['beat']}: citizen beat uses source fabric")
        if b["seat"] == "officer" and b["source"] != "fabric":
            problems.append(f"{b['beat']}: officer beat uses source {b['source']}")
    for pid, p in prompts.items():
        if p.get("seat") == "citizen" and "fabric_iq" in (p.get("expected") or {}).get("tools", []):
            problems.append(f"test-prompts.json: citizen prompt {pid} expects the fabric_iq tool")
    citizen = sum(b["seat"] == "citizen" for b in beats)
    g.check(L, f"Rahim's {citizen} citizen beats never use Fabric; Mei's beats always do", problems)

    # 3. fabric beat <-> test prompt <-> question bank
    problems = []
    fabric_beats = [b for b in beats if b["source"] == "fabric"]
    if not qrows:
        problems.append("no questions found in the question-bank.md main table")
    if len(qrows) > 3:
        problems.append(f"question-bank.md has {len(qrows)} Mei questions (max 3)")
    for q, row in qrows.items():
        p = prompts.get(row["prompt"])
        if p is None:
            problems.append(f"{q}: prompt {row['prompt']} not in test-prompts.json")
            continue
        exp = p.get("expected") or {}
        if p.get("question_id") != q:
            problems.append(f"{q}: prompt {row['prompt']} has question_id {p.get('question_id')}")
        if p.get("seat") != "officer":
            problems.append(f"{q}: prompt {row['prompt']} is not an officer prompt")
        if p.get("text", "").strip() != row["question"]:
            problems.append(f"{q}: question text differs between question-bank.md and test-prompts.json")
        if exp.get("reference") != f"content/fabric/reference-answers.json#{q}":
            problems.append(f"{q}: expected.reference should be content/fabric/reference-answers.json#{q}")
        if "fabric_iq" not in exp.get("tools", []):
            problems.append(f"{q}: expected.tools does not include fabric_iq")
        if row["gate"] == "?":
            problems.append(f"{q}: live gate must say strict or advisory")
        if q not in ref:
            problems.append(f"{q}: no reference answer (add it to r360.reference_answers)")
        if q not in LIVE_SHAPE:
            problems.append(f"{q}: no live-layer shape in validate-narrative.py LIVE_SHAPE")
        if not any(prompts.get(b["prompt"], {}).get("question_id") == q for b in fabric_beats):
            problems.append(f"{q}: no fabric beat in rahim.md uses it")
        gql = canonical_gql()
        if q not in gql:
            problems.append(f"{q}: no ```gql name={q}``` block in question-bank.md (the live graph check needs it)")
        total_key = LIVE_SHAPE.get(q, (None, None, None))[2]
        if total_key and f"{q}.{total_key}" not in gql:
            problems.append(f"{q}: no ```gql name={q}.{total_key}``` block in question-bank.md")
        for name, text in gql.items():
            if name.startswith(q) and RESIDENT_ID_RE.search(text):
                problems.append(f"{name}: canonical GQL names a resident_id")
    for b in fabric_beats:
        q = prompts.get(b["prompt"], {}).get("question_id")
        if q not in qrows:
            problems.append(f"{b['beat']}: prompt {b['prompt']} has question_id {q}, not in question-bank.md")
    for pid, p in prompts.items():
        if p.get("seat") == "officer" and p.get("question_id") not in qrows:
            problems.append(f"test-prompts.json: officer prompt {pid} has no question-bank.md question")
    g.check(L, f"{len(fabric_beats)} fabric beats <-> test prompts <-> {len(qrows)} question-bank questions", problems)

    # 4. glossary: verbatim definitions + no spelling drift
    problems = []
    coach_raw = COACH.read_text(encoding="utf-8")
    agent_raw = AGENT_INSTRUCTIONS.read_text(encoding="utf-8")
    base = cc.fenced_blocks(coach_raw).get("base", "")
    for t in glossary.get("terms", []):
        if t["definition"] not in base:
            problems.append(f"'{t['term']}' definition not verbatim in coach-instructions.md (base block)")
        if t["definition"] not in agent_raw:
            problems.append(f"'{t['term']}' definition not verbatim in data-agent-instructions.md")
    sources = {rel(NARRATIVE): body, rel(QBANK): cc.strip_code(QBANK.read_text(encoding="utf-8")),
               rel(COACH): coach_raw, rel(AGENT_INSTRUCTIONS): agent_raw,
               rel(PROMPTS): "\n".join(p.get("text", "") for p in prompts.values())}
    for path in sorted((ROOT / "content" / "labs").glob("*.md")):
        sources[rel(path)] = cc.strip_code(path.read_text(encoding="utf-8"))
    rules = spelling_rules(glossary)
    identifiers = ontology_identifiers()
    for name, text in sources.items():
        for canonical, pat, exact in rules:
            for m in pat.finditer(text):
                if m.group(0) in identifiers:
                    continue
                if exact or _skeleton(m.group(0)) != _skeleton(canonical):
                    line = text.count("\n", 0, m.start()) + 1
                    problems.append(f"{name}:{line}: '{m.group(0)}' should be '{canonical}'")
    g.check(L, f"glossary: {len(glossary.get('terms', []))} definitions verbatim; spelling consistent in "
               f"{len(sources)} files", problems)

    # 5. no resident_id where only aggregates belong
    problems = []
    for pid, p in prompts.items():
        if p.get("seat") == "officer" and RESIDENT_ID_RE.search(p.get("text", "") + json.dumps(p.get("expected", {}))):
            problems.append(f"test-prompts.json: officer prompt {pid} names a resident_id")
    if RESIDENT_ID_RE.search(QBANK.read_text(encoding="utf-8")):
        problems.append("question-bank.md names a resident_id")
    if RESIDENT_ID_RE.search(json.dumps(ref)):
        problems.append("reference answers contain a resident_id")
    for b in fabric_beats:
        if RESIDENT_ID_RE.search(b["text"]):
            problems.append(f"{b['beat']}: fabric beat names a resident_id")
    g.check(L, "no resident_id in officer prompts, question bank, fabric beats or reference answers", problems)

    # 6. numbers only from the reference answers
    problems = []
    for b in beats:
        text = ALLOWED_DIGITS_RE.sub("", FILLED_RE.sub("", PLACEHOLDER_RE.sub("", b["text"])))
        nums = NUMBER_RE.findall(text)
        if nums:
            problems.append(f"{b['beat']}: hard-coded number(s) {', '.join(nums)}; use {{{{ref:...}}}}")
    filled, problems_fill = 0, []
    for path in fill_files():
        text = path.read_text(encoding="utf-8")
        for m in PLACEHOLDER_RE.finditer(text):
            try:
                lookup(ref, m.group(1))
                problems_fill.append(f"{rel(path)}: {{{{ref:{m.group(1)}}}}} not filled (run --fill)")
            except KeyError:
                problems_fill.append(f"{rel(path)}: unknown reference key {m.group(1)}")
        for m in FILLED_RE.finditer(text):
            filled += 1
            try:
                want = fmt(m.group(1), lookup(ref, m.group(1)))
            except KeyError:
                problems_fill.append(f"{rel(path)}: unknown reference key {m.group(1)}")
                continue
            if m.group(2) != want:
                problems_fill.append(f"{rel(path)}: {m.group(1)} shows '{m.group(2)}', reference is '{want}' (run --fill)")
    if not (PLACEHOLDER_RE.search(body) or FILLED_RE.search(body)):
        problems_fill.append("rahim.md quotes no reference values")
    g.check(L, "beats quote numbers only through {{ref:...}}", problems)
    g.check(L, f"{filled} reference values filled and current in rahim.md + lab pages", problems_fill)


# ---------------------------------------------------------------------------------------------------
# Data layer
# ---------------------------------------------------------------------------------------------------

def data_layer(g: Gate, t: dict, ref: dict, glossary: dict, check_only: bool) -> None:
    L = "data"
    res = {r["resident_id"]: r for r in t["resident_360"]}
    occ = {o["event_occurrence_id"]: o for o in t["dim_event_occurrence"]}
    regions = {r["region"] for r in t["dim_region"]}
    progs = {p["programme_name"] for p in t["dim_programme"]}
    counts = ", ".join(f"{k} {len(v):,}" for k, v in t.items())
    g.add(L, f"Resident 360 rebuilt with scripts/r360.py: {counts}", "PASS")

    problems = []
    if len(res) != len(t["resident_360"]):
        problems.append("duplicate resident_id in resident_360")
    if len(occ) != len(t["dim_event_occurrence"]):
        problems.append("duplicate event_occurrence_id in dim_event_occurrence")
    for f in t["fact_event_attendance"]:
        if f["resident_id"] not in res:
            problems.append(f"attendance -> unknown resident {f['resident_id']}")
        if f["event_occurrence_id"] not in occ:
            problems.append(f"attendance -> unknown event occurrence {f['event_occurrence_id']}")
    for e in t["fact_programme_enrolment"]:
        if e["resident_id"] not in res:
            problems.append(f"enrolment -> unknown resident {e['resident_id']}")
        if e["programme_name"] not in progs:
            problems.append(f"enrolment -> unknown programme {e['programme_name']}")
    problems += [f"event occurrence {o['event_occurrence_id']} held in unknown region {o['region']}"
                 for o in occ.values() if o["region"] not in regions]
    problems += [f"resident {r['resident_id']} lives in unknown region {r['region']}"
                 for r in res.values() if r["region"] not in regions]
    g.check(L, f"joins: {len(t['fact_event_attendance']):,} attendance rows -> resident + event occurrence -> region; "
               f"{len(t['fact_programme_enrolment']):,} enrolment rows -> resident + programme", problems)

    problems = []
    if regions != set(glossary.get("regions", [])):
        problems.append(f"dim_region {sorted(regions)} != glossary regions {sorted(glossary.get('regions', []))}")
    if progs != set(glossary.get("programmes", [])):
        problems.append(f"dim_programme {sorted(progs)} != glossary programmes {sorted(glossary.get('programmes', []))}")
    for q in ("q_disengaged_regions", "q_dropped_attended_heldin"):
        problems += [f"{q}: unknown region {r['region']}" for r in ref[q]["rows"] if r["region"] not in regions]
    g.check(L, "region and programme names match dim_region / dim_programme and the glossary", problems)

    problems = []
    for r in res.values():
        rule = int(r["avg_daily_steps"] < r360.DISENGAGED_STEPS and r["events_attended"] == 0
                   and r["programmes_dropped"] >= 1)
        if r["is_disengaged"] != rule:
            problems.append(f"{r['resident_id']}: is_disengaged {r['is_disengaged']} but the glossary rule gives {rule}")
        if r["region_is_hazy"] != int(r["region_psi"] >= r360.HAZY_PSI):
            problems.append(f"{r['resident_id']}: region_is_hazy {r['region_is_hazy']} with PSI {r['region_psi']}")
    g.check(L, f"glossary rules hold on all {len(res):,} residents (disengaged, hazy)", problems)

    # Rahim: the row, the profile tool, the intake documents and the story agree
    facts = r360.rahim_facts(t)
    rid = facts["resident_id"]
    problems = []
    citizens = json.loads(CITIZENS.read_text(encoding="utf-8"))["citizens"]
    c = next((x for x in citizens if x.get("resident_id") == rid), None)
    if c is None:
        problems.append(f"citizens.json has no {rid}")
    else:
        pairs = {"region": "region", "planning_area": "planning_area", "age_band": "age_band",
                 "screening_risk": "screening_risk", "avg_daily_steps": "avg_daily_steps",
                 "avg_mvpa_min": "avg_mvpa_min_per_day", "nsc_progress_pct": "nsc_progress_pct",
                 "programmes_dropped": "programmes_dropped", "events_attended": "events_attended",
                 "events_booked": "events_booked", "meal_logs": "meal_logs",
                 "healthpoints_balance": "healthpoints_balance", "region_psi": "region_psi",
                 "region_is_hazy": "region_is_hazy", "is_disengaged": "is_disengaged"}
        problems += [f"citizens.json {ck} {c.get(ck)!r} != resident_360 {fk} {facts[fk]!r}"
                     for fk, ck in pairs.items() if c.get(ck) != facts[fk]]
        dropped = sorted(p["programme_name"] for p in c.get("programmes", []) if p.get("status") == "Dropped")
        if dropped != facts["dropped_programmes"]:
            problems.append(f"citizens.json dropped programmes {dropped} != {facts['dropped_programmes']}")
    low, high = (int(x) for x in re.findall(r"\d+", facts["age_band"])[:2])
    meal_median = statistics.median(r["meal_logs"] for r in res.values())
    story = [
        ("age band 60-64", facts["age_band"] == "60-64"),
        ("Woodlands, North region", facts["planning_area"] == "Woodlands" and facts["region"] == "North"),
        ("drifting on the National Steps Challenge (progress < 50%)", (facts["nsc_progress_pct"] or 0) < 50),
        (f"rarely logs meals (below the resident median of {meal_median:g})", facts["meal_logs"] < meal_median),
        ("hazy home region (PSI >= 55)", facts["region_is_hazy"] == 1),
        ("dropped a programme", facts["programmes_dropped"] >= 1),
        ("elevated glucose, pre-diabetes range 6.1-6.9 mmol/L", 6.1 <= (facts["latest_glucose_mmol"] or 0) < 7.0),
        ("screening risk High", facts["screening_risk"] == "High"),
        ("at most 2 events attended", facts["events_attended"] <= 2),
        ("disengaged", facts["is_disengaged"] == 1),
    ]
    problems += [f"story says '{claim}', the row disagrees" for claim, ok in story if not ok]
    m = re.search(r"\*\*Rahim\*\*, (\d+), ([A-Za-z ]+?) \(([A-Za-z-]+) region\)", NARRATIVE.read_text(encoding="utf-8"))
    if not m:
        problems.append("rahim.md: cannot find the '**Rahim**, <age>, <area> (<region> region)' line")
    else:
        if not low <= int(m.group(1)) <= high:
            problems.append(f"rahim.md age {m.group(1)} is outside band {facts['age_band']}")
        if (m.group(2), m.group(3)) != (facts["planning_area"], facts["region"]):
            problems.append(f"rahim.md says {m.group(2)} ({m.group(3)}), row says {facts['planning_area']} ({facts['region']})")
    scr = (INTAKE / "rahim-screening-summary.md").read_text(encoding="utf-8")
    diary = (INTAKE / "rahim-activity-diary.md").read_text(encoding="utf-8")
    glucose = re.search(r"Fasting blood glucose \| ([\d.]+) mmol/L", scr)
    band = re.search(r"Overall risk band:\*\*\s*([A-Za-z ]+?)\s*$", scr, flags=re.MULTILINE)
    age = re.search(r"\*\*Age:\*\*\s*(\d+)", scr)
    area = re.search(r"\*\*Home area:\*\*\s*([A-Za-z ]+?)\s*$", scr, flags=re.MULTILINE)
    steps = [int(s.replace(",", "")) for s in
             re.findall(r"^\|\s*(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s*\|\s*([\d,]+)\s*\|", diary, flags=re.MULTILINE)]
    if not glucose or float(glucose.group(1)) != facts["latest_glucose_mmol"]:
        problems.append(f"screening summary glucose {glucose and glucose.group(1)} != {facts['latest_glucose_mmol']}")
    if not band or band.group(1) != facts["screening_risk"]:
        problems.append(f"screening summary risk band {band and band.group(1)} != {facts['screening_risk']}")
    if not age or not low <= int(age.group(1)) <= high:
        problems.append(f"screening summary age {age and age.group(1)} outside {facts['age_band']}")
    if not area or area.group(1) != facts["planning_area"]:
        problems.append(f"screening summary home area {area and area.group(1)} != {facts['planning_area']}")
    if len(steps) != 7 or abs(sum(steps) / 7 - facts["avg_daily_steps"]) > 50:
        problems.append(f"activity diary averages {sum(steps) / max(len(steps), 1):.0f} steps, row has {facts['avg_daily_steps']}")
    g.check(L, f"Rahim's row matches citizens.json, the two intake documents and the story ({len(story)} claims)",
            problems)

    # reference answers: internally consistent, then written
    problems = []
    qd = ref["q_disengaged_regions"]
    if sum(r["residents"] for r in qd["rows"]) != qd["total_residents"] or qd["total_residents"] != len(res):
        problems.append("q_disengaged_regions: residents per region do not add up to all residents")
    if sum(r["disengaged"] for r in qd["rows"]) != qd["disengaged_total"]:
        problems.append("q_disengaged_regions: disengaged per region do not add up")
    region_counts = {r["region"]: r["resident_count"] for r in t["dim_region"] if "resident_count" in r}
    region_dis = {r["region"]: r["disengaged_residents"] for r in t["dim_region"]}
    region_share = {r["region"]: r["disengaged_share_pct"] for r in t["dim_region"]}
    for r in qd["rows"]:
        if region_counts and region_counts.get(r["region"]) != r["residents"]:
            problems.append(f"q_disengaged_regions: {r['region']} {r['residents']} != dim_region.resident_count")
        if region_dis.get(r["region"]) != r["disengaged"]:
            problems.append(f"q_disengaged_regions: {r['region']} {r['disengaged']} != dim_region.disengaged_residents")
        if region_share.get(r["region"]) != r["share_pct"]:
            problems.append(f"q_disengaged_regions: {r['region']} {r['share_pct']}% != dim_region.disengaged_share_pct")
    prog_dis = {p["programme_name"]: p["disengaged_enrolled"] for p in t["dim_programme"]}
    for r in ref["q_programmes_disengaged_enrolled"]["rows"]:
        if prog_dis.get(r["programme_name"]) != r["disengaged_enrolled"]:
            problems.append(f"q_programmes_disengaged_enrolled: {r['programme_name']} {r['disengaged_enrolled']} "
                            f"!= dim_programme.disengaged_enrolled {prog_dis.get(r['programme_name'])}")
    qh = ref["q_dropped_attended_heldin"]
    if max(r["residents"] for r in qh["rows"]) > qh["distinct_residents"]:
        problems.append("q_dropped_attended_heldin: a region has more residents than the distinct total")
    g.check(L, "reference answers add up and match the gold aggregates (Region.resident_count / "
               "disengaged_residents / disengaged_share_pct, Programme.disengaged_enrolled, distinct totals)", problems)

    new = json.dumps(ref, indent=2, ensure_ascii=False) + "\n"
    old = REF_JSON.read_text(encoding="utf-8") if REF_JSON.exists() else None
    questions = [k for k in ref if k.startswith("q_")]
    if old == new:
        g.add(L, f"{rel(REF_JSON)} up to date ({len(questions)} questions + rahim)", "PASS")
    elif check_only:
        g.add(L, f"{rel(REF_JSON)} is out of date", "FAIL",
              ["run: python scripts/validate-narrative.py --fill   (then commit the JSON and the filled pages)"])
    else:
        REF_JSON.write_bytes(new.encode("utf-8"))
        g.add(L, f"{rel(REF_JSON)} {'written' if old is None else 'updated'} ({len(questions)} questions + rahim)",
              "PASS", [] if old is None else ["values changed: run --fill and review the narrative"])


# ---------------------------------------------------------------------------------------------------
# Live layer
# ---------------------------------------------------------------------------------------------------

def label_pattern(label: str) -> re.Pattern:
    m = re.match(r"^(.*?)\s*\(([^)]*)\)$", label)
    core, paren = (m.group(1), m.group(2)) if m else (label, None)
    pat = r"[\s,-]*".join(re.escape(w) for w in re.split(r"[\s-]+", core))
    if paren:
        pat += r"(?:\s*\(" + re.escape(paren) + r"\))?"
    return re.compile(r"(?<![\w-])" + pat + r"(?![\w-])", re.IGNORECASE)


def numbers(s: str) -> list[float]:
    return [float(x.replace(",", "")) for x in NUMBER_RE.findall(s)]


def find_rows(answer: str, labels: list[str], pct: bool = False) -> list[tuple[str, list[float]]]:
    """Rows of the answer that name exactly one label and carry numbers, in the order they appear.
    Markdown table rows win over prose (the headline sentence often names the top label next to a total);
    bullets and sentences count only when there is no table. "North" inside "North-East" is not North.
    pct=True keeps only percentages (numbers followed by %)."""
    lines = answer.splitlines()
    table = [ln for ln in lines if ln.lstrip().startswith("|")]
    return _scan_rows(table, labels, pct) or _scan_rows(lines, labels, pct)


def _scan_rows(lines: list[str], labels: list[str], pct: bool = False) -> list[tuple[str, list[float]]]:
    pats = {lab: label_pattern(lab) for lab in labels}
    out, seen = [], set()
    for line in lines:
        hits = [(lab, m.start(), m.end()) for lab, pat in pats.items() for m in pat.finditer(line)]
        hits = [h for h in hits if not any(o[1] <= h[1] and h[2] <= o[2] and o[2] - o[1] > h[2] - h[1] for o in hits)]
        labs = {h[0] for h in hits}
        if len(labs) != 1:
            continue
        lab = labs.pop()
        rest = line
        for h in sorted(hits, key=lambda h: -h[1]):
            rest = rest[:h[1]] + " " + rest[h[2]:]
        nums = [float(x) for x in PERCENT_RE.findall(rest)] if pct else numbers(rest)
        if lab in seen or not nums:
            continue
        seen.add(lab)
        out.append((lab, nums))
    return out


def judge(q: str, answer: str, refq: dict, is_error: bool) -> tuple[list[str], list[tuple[str, list[float]]]]:
    label_key, count_key, total_key = LIVE_SHAPE[q]
    rows = refq["rows"]
    problems = []
    if is_error:
        problems.append("the data agent says it could not query the ontology (numbers are not grounded)")
    if RESIDENT_ID_RE.search(answer):
        problems.append("the answer contains a resident_id")
    found = find_rows(answer, [r[label_key] for r in rows])
    need = min(3, len(rows))
    if len(found) < need:
        problems.append(f"not grouped: {len(found)} {label_key} rows recognised (need >= {need})")
    rank = {r[label_key]: i for i, r in enumerate(rows)}
    value = {r[label_key]: r[count_key] for r in rows}
    for lab, nums in found:
        if value[lab] not in nums:
            shown = ", ".join(f"{n:g}" for n in nums)
            problems.append(f"{lab}: reference {count_key} = {value[lab]}, the answer shows {shown}")
    expected = sorted((lab for lab, _ in found), key=rank.get)
    for pos, (lab, _) in enumerate(found):
        if abs(pos - expected.index(lab)) > 1:
            problems.append(f"{lab} is listed at position {pos + 1}; reference position {expected.index(lab) + 1} (> +-1 rank)")
    if total_key and refq[total_key] not in numbers(answer):
        problems.append(f"the answer does not give the total {total_key} = {refq[total_key]}")
    if "share_pct" in rows[0]:
        share = {r[label_key]: r["share_pct"] for r in rows}
        for lab, pcts in find_rows(answer, list(share), pct=True):
            if not any(abs(p - share[lab]) <= 0.1 for p in pcts):
                shown = ", ".join(f"{p:g}%" for p in pcts)
                problems.append(f"{lab}: reference share {share[lab]}%, the answer shows {shown}")
    return problems, found


def load_env(env: str) -> None:
    os.environ["AZURE_ENV_NAME"] = env
    path = ROOT / ".azure" / env / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, _, v = line.partition("=")
                if k.strip() in ("FABRIC_WORKSPACE_ID", "FABRIC_DATA_AGENT_ID", "FABRIC_GRAPH_MODEL_ID", "AZURE_TENANT_ID"):
                    os.environ.setdefault(k.strip(), v.strip().strip('"'))
    if not os.environ.get("AZURE_TENANT_ID"):
        try:
            tid = wsconfig.lookup(wsconfig.load(env), f"environments.{env}.tenant_id")
        except (KeyError, TypeError, SystemExit):
            tid = None
        if tid and tid != "TODO":
            os.environ["AZURE_TENANT_ID"] = str(tid)


def default_env() -> str:
    if os.environ.get("AZURE_ENV_NAME"):
        return os.environ["AZURE_ENV_NAME"]
    cfg = ROOT / ".azure" / "config.json"
    if cfg.exists():
        return json.loads(cfg.read_text(encoding="utf-8")).get("defaultEnvironment", "")
    return ""


def graph_check(g: Gate, ref: dict, qrows: dict, only: list[str]) -> None:
    """Run the canonical GQL on the ontology's graph model and require the reference answers exactly.
    Separates "the published graph is wrong" from "the agent wrote a different query"."""
    import fabriclib as fl  # noqa: PLC0415
    L = "live"
    gid, ws = os.environ.get("FABRIC_GRAPH_MODEL_ID"), os.environ.get("FABRIC_WORKSPACE_ID")
    if not gid or not ws:
        g.add(L, "graph check: canonical GQL returns the reference answers", "SKIP",
              ["FABRIC_GRAPH_MODEL_ID / FABRIC_WORKSPACE_ID not in the azd env (run scripts/fabric/deploy.sh)"])
        return
    gql = canonical_gql()
    fab = fl.Fabric()
    problems, lat = [], []
    for q in qrows:
        if only and q not in only:
            continue
        label_key, count_key, total_key = LIVE_SHAPE[q]
        jobs = [(q, None)] + ([(f"{q}.{total_key}", total_key)] if total_key else [])
        jobs += [(f"{q}.gold", None)] if f"{q}.gold" in gql else []
        for name, tkey in jobs:
            start = time.time()
            try:
                status, _, body = fab.call("POST", f"/v1/workspaces/{ws}/GraphModels/{gid}/executeQuery?preview=true",
                                           {"query": gql[name]})
            except (SystemExit, Exception) as e:  # noqa: BLE001
                problems.append(f"{name}: query failed: {str(e)[:200]}")
                continue
            lat.append(time.time() - start)
            code = ((body or {}).get("status") or {}).get("code")
            data = ((body or {}).get("result") or {}).get("data") or []
            if code != "00000":
                problems.append(f"{name}: GQL status {code}: {((body or {}).get('status') or {}).get('description')}")
                continue
            if tkey:
                got = next(iter(data[0].values()), None) if data else None
                if got != ref[q][tkey]:
                    problems.append(f"{name}: graph says {got}, reference {ref[q][tkey]}")
                continue
            got = {row.get(label_key): row.get(count_key) for row in data}
            want = {row[label_key]: row[count_key] for row in ref[q]["rows"]}
            if got != want:
                diff = sorted(k for k in set(got) | set(want) if got.get(k) != want.get(k))
                problems.append(f"{name}: " + "; ".join(f"{k} graph {got.get(k)} vs reference {want.get(k)}"
                                                        for k in diff[:6]))
            for row in data:
                if "share_pct" in row:
                    want_pct = next((r["share_pct"] for r in ref[q]["rows"] if r[label_key] == row.get(label_key)), None)
                    if want_pct is None or abs(float(row["share_pct"] or 0) - want_pct) > 0.05:
                        problems.append(f"{name}: {row.get(label_key)} share {row['share_pct']} vs reference {want_pct}")
    timing = f"; {min(lat):.0f}-{max(lat):.0f} s per query" if lat else ""
    g.check(L, f"graph check: canonical GQL on the graph model returns the reference answers{timing}", problems)


def live_layer(g: Gate, ref: dict, prompts: dict, qrows: dict, runs: int, only: list[str],
               pause: float = 0) -> list[dict]:
    L = "live"
    sys.path.insert(0, str(ROOT / "scripts" / "fabric"))
    import ask as fask  # noqa: PLC0415
    import fabriclib as fl  # noqa: PLC0415

    try:
        ws, agent = fask.resolve()
        token, token_at = fl.az_token(fl.FABRIC, os.environ.get("AZURE_TENANT_ID") or None), time.time()
    except (SystemExit, Exception) as e:  # noqa: BLE001
        g.add(L, "published data agent reachable", "FAIL", [str(e)[:300], "run az login, then scripts/fabric/deploy.sh"])
        return []
    graph_check(g, ref, qrows, only)
    records: list[dict] = []
    first = True
    for q, row in qrows.items():
        if only and q not in only:
            continue
        text = prompts[row["prompt"]]["text"]
        for i in range(1, runs + 1):
            if not first and pause:
                time.sleep(pause)
            first = False
            if time.time() - token_at > 40 * 60:
                token, token_at = fl.az_token(fl.FABRIC, os.environ.get("AZURE_TENANT_ID") or None), time.time()
            start = time.time()
            try:
                res = fask.ask(text, ws, agent, token)
                answer, seconds, err = res["answer"], res["seconds"], res["is_error"]
            except Exception as e:  # noqa: BLE001
                answer, seconds, err = f"(call failed: {str(e)[:300]})", round(time.time() - start, 1), True
            problems, found = judge(q, answer, ref[q], err)
            status = "PASS" if not problems else ("WARN" if row["gate"] == "advisory" else "FAIL")
            top = found[0][0] if found else "-"
            slow = " SLOW" if seconds > SLOW_S else ""
            print(f"        {q} run {i}/{runs}: {status} in {seconds:.0f} s{slow}; top {top}; "
                  f"{len(found)} rows" + (f"; {problems[0]}" if problems else ""), flush=True)
            records.append({"question_id": q, "gate": row["gate"], "run": i, "seconds": seconds, "status": status,
                            "top": top, "rows": len(found), "problems": problems, "answer": answer})
        mine = [r for r in records if r["question_id"] == q]
        lat = [r["seconds"] for r in mine]
        ok = sum(r["status"] == "PASS" for r in mine)
        g.check(L, f"{q} ({row['gate']}): {ok}/{len(mine)} runs match the reference; "
                   f"{min(lat):.0f}-{max(lat):.0f} s", [f"run {r['run']}: {p}" for r in mine for p in r["problems"]],
                advisory=row["gate"] == "advisory")
        slow = [r for r in mine if r["seconds"] > SLOW_S]
        if slow:
            g.add(L, f"{q}: {len(slow)} answer(s) slower than {SLOW_S} s", "WARN",
                  [f"run {r['run']}: {r['seconds']:.0f} s" for r in slow])
    g.add(L, *coach_routing())
    return records


def coach_routing() -> tuple[str, str, list[str]]:
    """The coach-routing row comes from the latest Lab 3 Builder run with --fabric (lab3_tools.py records the
    two checks in content/assets/.runs/lab3-<INITIALS>.json; validate-builder-rail.py runs it as INITIALS=test)."""
    name = "coach routing via the LiveWell agent (Fabric IQ call for Mei, none for Rahim)"
    need = ["fabric_q_disengaged_regions: Fabric IQ tool called",
            "lab1_prediabetes_eat on the Fabric coach: no Fabric call"]
    runs = sorted((ROOT / "content" / "assets" / ".runs").glob("lab3-*.json"), key=lambda p: p.stat().st_mtime)
    for path in reversed(runs):
        checks = json.loads(path.read_text(encoding="utf-8")).get("results", {}).get("checks", {})
        if all(k in checks for k in need):
            when = dt.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            details = [f"{path.name} ({when}): " + "; ".join(f"{k} = {'PASS' if checks[k] else 'FAIL'}" for k in need)]
            return name, "PASS" if all(checks[k] for k in need) else "FAIL", details
    return name, "SKIP", ["no Lab 3 run with the Fabric step yet: `make -C content/assets validate-rail` "
                          "(or `lab3_tools.py --fabric`) records it"]


# ---------------------------------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------------------------------

def git_commit() -> str:
    try:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout
        return head + ("+local changes" if dirty.strip() else "")
    except OSError:
        return "unknown"


def cell(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def write_report(g: Gate, records: list[dict], ref: dict, qrows: dict, prompts: dict, cmd: str,
                 env: str, started: dt.datetime) -> Path:
    DEMOS.mkdir(exist_ok=True)
    path = DEMOS / f"NARRATIVE-VALIDATION-{started.date().isoformat()}.md"
    fails, warns, skips = g.count("FAIL"), g.count("WARN"), g.count("SKIP")
    verdict = "FAIL" if fails else "PASS"
    out = [f"# Narrative validation, {started.date().isoformat()}", "",
           f"Generated by `{cmd}` at {started.strftime('%H:%M')} (local time) on commit `{git_commit()}`"
           + (f", azd environment `{env}`." if env else "."), "",
           f"**Gate: {verdict}**: {g.count('PASS')} passed, {fails} failed, {warns} warnings, {skips} skipped. "
           "WARN and SKIP do not fail the gate (SPEC.md §11.1).", "",
           "## Checks", "", "| Layer | Check | Result | Detail |", "|---|---|---|---|"]
    for r in g.rows:
        detail = "; ".join(r["details"][:6]) + (f"; … {len(r['details']) - 6} more" if len(r["details"]) > 6 else "")
        out.append(f"| {r['layer']} | {cell(r['check'])} | {r['status']} | {cell(detail) or '—'} |")
    if records:
        lat = [r["seconds"] for r in records]
        out += ["", "## Live runs (published data agent, user token)", "",
                f"{len(records)} calls; latency min {min(lat):.0f} s, median {statistics.median(lat):.0f} s, "
                f"max {max(lat):.0f} s (expect 30-90 s; > {SLOW_S} s is flagged).", "",
                "| Question | Gate | Run | Latency | Result | Top of the answer | Reference top | Rows | Notes |",
                "|---|---|---|---|---|---|---|---|---|"]
        for r in records:
            label_key = LIVE_SHAPE[r["question_id"]][0]
            ref_top = ref[r["question_id"]]["rows"][0][label_key]
            slow = " ⚠️" if r["seconds"] > SLOW_S else ""
            out.append(f"| `{r['question_id']}` | {r['gate']} | {r['run']} | {r['seconds']:.0f} s{slow} | {r['status']} "
                       f"| {cell(r['top'])} | {cell(ref_top)} | {r['rows']} | {cell('; '.join(r['problems'])) or '—'} |")
    out += ["", "## Reference answers", "",
            "From `content/fabric/reference-answers.json` (scripts/r360.py gold build). The story quotes only these.", ""]
    for q, row in qrows.items():
        if q not in ref or q not in LIVE_SHAPE:
            continue
        label_key, count_key, total_key = LIVE_SHAPE[q]
        rows = ref[q]["rows"]
        extra = [k for k in rows[0] if k not in (label_key, count_key)]
        out += [f"**`{q}`** ({row['gate']}): {prompts[row['prompt']]['text']}", "",
                f"| {label_key} | {count_key} | " + " | ".join(extra) + " |",
                "|---|---|" + "---|" * len(extra)]
        out += [f"| {r[label_key]} | {r[count_key]} | " + " | ".join(str(r[k]) for k in extra) + " |" for r in rows]
        if total_key:
            out += ["", f"{total_key}: {ref[q][total_key]}"]
        out.append("")
    if records:
        out += ["## Answers as received", ""]
        for r in records:
            out += [f"<details><summary><code>{r['question_id']}</code> run {r['run']}: {r['status']}, "
                    f"{r['seconds']:.0f} s</summary>", "", r["answer"].strip(), "", "</details>", ""]
    path.write_bytes(("\n".join(out).rstrip() + "\n").encode("utf-8"))
    return path


# ---------------------------------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--layers", default="static,data", help="comma list of static,data,live, or all")
    ap.add_argument("--env", default="", help="azd environment for the live layer (default: AZURE_ENV_NAME, then azd default)")
    ap.add_argument("--runs", type=int, default=3, help="live calls per question (default 3)")
    ap.add_argument("--questions", default="", help="live layer only: comma list of question_ids (default all)")
    ap.add_argument("--pause", type=float, default=20,
                    help="live layer: seconds between data-agent calls so an F2 capacity is not throttled (default 20)")
    ap.add_argument("--fill", action="store_true", help="fill / refresh {{ref:...}} values before checking")
    ap.add_argument("--check", action="store_true", help="never write reference-answers.json (CI)")
    ap.add_argument("--report", action="store_true", help="write the report even without the live layer")
    ap.add_argument("--no-report", action="store_true", help="never write the report")
    a = ap.parse_args()
    layers = list(LAYERS) if a.layers.strip() == "all" else [x.strip() for x in a.layers.split(",") if x.strip()]
    bad = [x for x in layers if x not in LAYERS]
    if bad or not layers:
        ap.error(f"unknown layer(s) {bad}; use static, data, live or all")
    started = dt.datetime.now()
    cmd = "python scripts/validate-narrative.py " + " ".join(sys.argv[1:])

    t = r360.build()
    ref = reference(t)
    bank = json.loads(PROMPTS.read_text(encoding="utf-8"))
    prompts = bank["prompts"]
    glossary = yaml.safe_load(GLOSSARY.read_text(encoding="utf-8"))
    qrows = parse_qbank()
    env = ""

    if a.fill:
        changed = fill(ref)
        print(f"[fill] {len(changed)} file(s) updated" + (": " + ", ".join(changed) if changed else ""))
    g = Gate()
    if "static" in layers:
        static_layer(g, ref, prompts, glossary, qrows)
    if "data" in layers:
        data_layer(g, t, ref, glossary, a.check)
    records: list[dict] = []
    if "live" in layers:
        env = a.env or default_env()
        if not env:
            ap.error("the live layer needs --env (or AZURE_ENV_NAME / an azd default environment)")
        load_env(env)
        only = [x.strip() for x in a.questions.split(",") if x.strip()]
        records = live_layer(g, ref, prompts, qrows, a.runs, only, a.pause)

    fails = g.count("FAIL")
    print(f"\n{g.count('PASS')} passed, {fails} failed, {g.count('WARN')} warnings, {g.count('SKIP')} skipped"
          f"  ->  gate {'FAIL' if fails else 'PASS'}")
    if (records or a.report) and not a.no_report:
        print(f"report: {rel(write_report(g, records, ref, qrows, prompts, cmd, env, started))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
