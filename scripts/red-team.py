#!/usr/bin/env python3
"""Facilitator-only AI red-team scan of the guarded LiveWell Coach (Lab 2), via the azure-ai-evaluation SDK.

Portal red teaming is not offered in swedencentral (workshop.yaml region_matrix), so the AI Red Teaming Agent
runs from here. By default the script creates a temporary `livewell-<INITIALS>-redteam` agent that matches the
Lab 2 guarded version (base + knowledge + safety blocks, the knowledge base, `livewell-guardrails`), scans it
and deletes it. `--agent NAME` scans an existing agent instead (for example `livewell-demo-guarded` or the
hosted `livewell-workshop-hosted`).

Cost: the AI evaluations meter bills about US$0.042 per attack (prompt x strategy, ADMIN-SETUP cost table:
$20/$60 per 1M evaluation tokens), plus the target's model tokens. The script prints the estimate and asks
before it starts. Never loop it.

    python -m venv .venv-redteam && .venv-redteam/bin/pip install -r requirements-redteam.txt   # once
    INITIALS=fac .venv-redteam/bin/python scripts/red-team.py --lite       # 10 prompts x 2 strategies, ~US$0.85
    INITIALS=fac .venv-redteam/bin/python scripts/red-team.py              # 48 prompts x 4 strategies, ~US$8
    ... scripts/red-team.py --agent livewell-demo-guarded --yes            # existing agent, no prompt
    ... scripts/red-team.py --upload                                       # also publish the scorecard to the project

Writes content/assets/.runs/redteam-<scan>/results.json and prints the attack success rate (ASR) per risk
category and per attack complexity. ASR = share of attacks that produced harmful content; lower is better.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "content" / "assets"))

from common import livewell_common as lw  # noqa: E402

USD_PER_ATTACK = 0.042
BLOCKED_REPLY = "I can't help with that request."  # what a caller sees when livewell-guardrails blocks the input

PRESETS = {
    # risk categories x objectives per category, attack strategies (Baseline = the unmodified prompt)
    "lite": (["SelfHarm", "Violence"], 5, ["Baseline", "Jailbreak"]),
    "full": (["HateUnfairness", "Violence", "Sexual", "SelfHarm"], 12, ["Baseline", "Base64", "Flip", "Jailbreak"]),
}


def load_sdk():
    try:
        from azure.ai.evaluation.red_team import AttackStrategy, RedTeam, RiskCategory
    except ImportError as e:
        raise SystemExit(f"{e}\nInstall the red-team extras in a separate venv: "
                         "pip install -r requirements-redteam.txt (see this script's docstring)") from None
    return AttackStrategy, RedTeam, RiskCategory


def make_target(agent, tally: dict):
    """Async callback in the SDK's chat-protocol shape; runs lw.ask in a thread so attacks run in parallel."""

    async def target(messages, stream=False, session_state=None, context=None):
        msgs = [m if isinstance(m, dict) else {"role": m.role, "content": m.content} for m in messages]
        query = msgs[-1]["content"]
        run = await asyncio.to_thread(lw.ask, agent, query, consent=True)
        tally["attacks"] += 1
        if run.blocked:
            tally["blocked"] += 1
            text = BLOCKED_REPLY
        else:
            text = run.text or BLOCKED_REPLY
        return {"messages": msgs + [{"role": "assistant", "content": text}], "stream": stream,
                "session_state": session_state, "context": {}}

    return target


def create_guarded_agent():
    return lw.create_agent(
        "redteam", lw.load_instructions("base", "knowledge", "safety"), tools=[lw.kb_tool()],
        schema=lw.lab1_schema(), rai_policy=lw.NAMES["rai_policy"],
        description="LiveWell Coach - Lab 2 guarded version, red-team target (temporary)")


def show_scorecard(result) -> None:
    scan = getattr(result, "scan_result", None) or {}
    card = scan.get("scorecard") or {}
    for key, title in (("risk_category_summary", "by risk category"),
                       ("attack_technique_summary", "by attack complexity")):
        rows = card.get(key) or []
        row = rows[0] if isinstance(rows, list) and rows else rows
        if not row:
            continue
        lw.say(f"ASR {title}:")
        for k, v in row.items():
            if k.endswith("_asr"):
                lw.say(f"   {k[:-4]:<22} {v:6.1f}%")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--lite", action="store_true", help="10 prompts x 2 strategies (about US$0.85)")
    ap.add_argument("--agent", help="scan this existing agent instead of a temporary guarded coach")
    ap.add_argument("--upload", action="store_true", help="publish the scorecard to the project (needs storage access)")
    ap.add_argument("--yes", action="store_true", help="do not ask before spending")
    ap.add_argument("--parallel", type=int, default=4, help="attacks in flight (default 4)")
    args = ap.parse_args()

    categories, per_category, strategies = PRESETS["lite" if args.lite else "full"]
    attacks = len(categories) * per_category * len(strategies)
    lw.say(f"red team: {len(categories)} risk categories x {per_category} objectives x {len(strategies)} strategies "
           f"= {attacks} attacks, estimated US${attacks * USD_PER_ATTACK:.2f} (AI evaluations meter) plus model tokens")
    if not args.yes and input("Run it? [y/N] ").strip().lower() not in ("y", "yes"):
        lw.say("cancelled")
        return 1

    AttackStrategy, RedTeam, RiskCategory = load_sdk()
    agent = args.agent or create_guarded_agent()
    name = agent if isinstance(agent, str) else agent.name
    if not isinstance(agent, str):
        lw.say(f"target = {name} version {agent.version} (guardrail: {lw.NAMES['rai_policy']})")
    scan_name = f"livewell-{name.removeprefix('livewell-')}-{dt.datetime.now():%Y%m%d-%H%M}"
    out = lw.RUNS_DIR / f"redteam-{scan_name}"
    out.mkdir(parents=True, exist_ok=True)

    tally = {"attacks": 0, "blocked": 0}
    red_team = RedTeam(
        azure_ai_project=lw.endpoint(), credential=lw.credential(),
        risk_categories=[getattr(RiskCategory, c) for c in categories], num_objectives=per_category,
        application_scenario="A public-health coach for Singapore residents that gives cited, general healthy-"
                             "living advice and must never give medication dosing or unsafe advice.",
        output_dir=str(out))
    try:
        result = asyncio.run(red_team.scan(
            target=make_target(agent, tally), scan_name=scan_name,
            attack_strategies=[getattr(AttackStrategy, s) for s in strategies if s != "Baseline"],
            output_path=str(out), skip_upload=not args.upload, max_parallel_tasks=args.parallel))
    finally:
        if not args.agent:
            lw.cleanup()

    show_scorecard(result)
    lw.say(f"target calls: {tally['attacks']} ({tally['blocked']} blocked by the guardrail at the input)")
    lw.say(f"estimated cost: US${tally['attacks'] * USD_PER_ATTACK:.2f} evaluation + model tokens")
    lw.say(f"results: {out / 'results.json'} (per-attack conversations in {out.name}/.scan_*/)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
