#!/usr/bin/env python3
"""Create or update the facilitator demo agents `livewell-demo-*` (T-3, after build-kb and connect-tools).

They are the Navigator agent at the end of each lab, built with the same instruction blocks, tools, response
formats and guardrail as the portal track, so facilitators can demo, record and fall back on them:

  lab0       livewell-demo-lab0      base block on model-router (Lab 0)
  knowledge  livewell-demo-kb        + knowledge block, Foundry IQ knowledge base, lab1 JSON schema (Lab 1)
  guarded    livewell-demo-guarded   + safety block and livewell-guardrails (Lab 2 comparator)
  tools      livewell-demo-tools     + tools block: livewell_profile (OpenAPI), activities MCP with approval
                                     for register_interest, memory, evidence JSON schema, gpt-5.4-mini (Lab 3)
  fabric     livewell-demo-fabric    + fabric block and the Fabric IQ tool (Fabric step; FABRIC_BRIDGE only)

Every tool runs server-side (no client-side function calls), so the agents work in the portal playground.
It also registers the shared `livewell-eval` dataset (content/eval/livewell-eval.jsonl) that the portal
evaluation wizard picks in Lab 2 (skip with --no-dataset).
Names come from agent_naming.demo_agents in content/config/workshop.yaml. The script only ever writes those
names; participant cleanup (livewell_common.cleanup) never deletes them. A new version is created only when
the definition changed (a hash is kept in the version metadata), so re-running is safe.

    python demos/create-demo-agents.py                   # create/update all, then list them
    python demos/create-demo-agents.py --check           # report only; exit 1 if missing or out of date
    python demos/create-demo-agents.py --roles lab0,kb   # a subset (role keys or full names)
    python demos/create-demo-agents.py --no-memory       # tools/fabric agents without memory

Needs the facilitator's azd env (AZURE_ENV_NAME) with Foundry Project Manager (or higher) on the project.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "content" / "assets"))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from common import livewell_common as lw  # noqa: E402

ORDER = ["lab0", "knowledge", "guarded", "tools", "fabric"]
ALIASES = {"kb": "knowledge"}
MEMORY_STORE = f"{lw.NAMING['demo_prefix']}memory"
MEMORY_SCOPE = "{{$userId}}"  # each signed-in viewer gets their own memories, as in the portal


def demo_names() -> dict[str, str]:
    names = dict(lw.NAMING["demo_agents"])
    for role, name in names.items():
        if not name.startswith(lw.NAMING["demo_prefix"]):
            raise SystemExit(f"workshop.yaml demo agent {role}={name} does not start with {lw.NAMING['demo_prefix']}")
    return names


def pick_roles(spec: str | None) -> list[str]:
    names = demo_names()
    if not spec:
        return [r for r in ORDER if r in names]
    by_name = {v: k for k, v in names.items()}
    roles = []
    for item in [s.strip() for s in spec.split(",") if s.strip()]:
        role = ALIASES.get(item, by_name.get(item, item))
        if role not in names:
            raise SystemExit(f"unknown demo agent {item!r}; choose from {', '.join(ORDER)}")
        roles.append(role)
    return roles


def definition(role: str, *, memory: bool = True, guardrail: str | None = None) -> tuple[dict, str]:
    """PromptAgentDefinition keyword arguments and a description for one demo role. smoke-test.py builds its
    temporary agents from the same function (with memory=False)."""
    m = lw.models()
    guardrail = guardrail or lw.NAMES["rai_policy"]

    def text(schema: dict, name: str):
        return m.PromptAgentDefinitionTextOptions(format=m.TextResponseFormatJsonSchema(
            name=name, schema=lw.strict_schema(schema), strict=True))

    rai = m.RaiConfig(rai_policy_name=lw.rai_policy_id(guardrail))
    if role == "lab0":
        return {"model": lw.DEFAULT_MODEL, "instructions": lw.load_instructions("base")}, \
            "LiveWell demo - Lab 0: base instructions on model-router"
    if role == "knowledge":
        return {"model": lw.DEFAULT_MODEL, "instructions": lw.load_instructions("base", "knowledge"),
                "tools": [lw.kb_tool()], "text": text(lw.lab1_schema(), "livewell_lab1_answer")}, \
            "LiveWell demo - Lab 1: Foundry IQ knowledge base and the lab1 JSON contract"
    if role == "guarded":
        return {"model": lw.DEFAULT_MODEL, "instructions": lw.load_instructions("base", "knowledge", "safety"),
                "tools": [lw.kb_tool()], "text": text(lw.lab1_schema(), "livewell_lab1_answer"), "rai_config": rai}, \
            f"LiveWell demo - Lab 2: safety block and {guardrail} (comparator)"
    if role in ("tools", "fabric"):
        blocks = ["base", "knowledge", "safety", "tools"] + (["fabric"] if role == "fabric" else [])
        tools = [lw.profile_openapi_tool(), lw.kb_tool(), lw.activities_tool(approve_writes=True)]
        if memory:
            tools.append(lw.memory_tool(lw.ensure_memory_store(MEMORY_STORE), scope=MEMORY_SCOPE))
        if role == "fabric":
            tools.append(lw.fabric_tool())
        what = ("Fabric step: Fabric IQ tool for programme questions" if role == "fabric"
                else "Lab 3: profile OpenAPI, activities MCP with approval" + (", memory" if memory else ""))
        return {"model": lw.MEMORY_MODEL if memory else lw.DEFAULT_MODEL, "instructions": lw.load_instructions(*blocks),
                "tools": tools, "text": text(lw.evidence_schema(), "livewell_evidence"), "rai_config": rai}, \
            f"LiveWell demo - {what}"
    raise ValueError(role)


def spec_hash(kwargs: dict) -> str:
    body = lw.models().PromptAgentDefinition(**kwargs).as_dict()
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:16]


def upsert(name: str, kwargs: dict, description: str, *, rail: str = "demo", check: bool = False) -> tuple[str, object]:
    """Create a version when the definition changed. Returns (state, version or None)."""
    digest = spec_hash(kwargs)
    current = lw.agent_by_name(name)
    if current is not None and (getattr(current, "metadata", None) or {}).get("spec_hash") == digest:
        return "in sync", current
    if check:
        return ("missing" if current is None else "out of date"), current
    m = lw.models()
    version = lw.retry(lambda: lw.project().agents.create_version(
        agent_name=name, definition=m.PromptAgentDefinition(**kwargs), description=description,
        metadata={"workshop": "livewell", "rail": rail, "spec_hash": digest}), what=f"create {name}")
    return ("created" if current is None else "updated"), version


def tool_summary(version) -> str:
    out = []
    for t in getattr(version.definition, "tools", None) or []:
        kind = getattr(t, "type", "?")
        label = (getattr(t, "server_label", None) or getattr(getattr(t, "openapi", None), "name", None)
                 or getattr(t, "memory_store_name", None) or "")
        out.append(f"{kind}:{label}" if label else kind)
    return ", ".join(out) or "-"


def register_dataset(*, check: bool = False) -> tuple[str, str]:
    """The shared `livewell-eval` dataset the portal evaluation wizard (Lab 2 step 15) picks as Existing dataset.
    The version is the file's content hash, so an edited JSONL registers a new version and re-runs are no-ops."""
    name = lw.NAMING.get("eval_dataset", "livewell-eval")
    version = hashlib.sha256(lw.EVAL_FILE.read_bytes()).hexdigest()[:8]
    ds = lw.project().datasets
    try:
        ds.get(name=name, version=version)
        return name, f"in sync (v{version})"
    except Exception:
        if check:
            return name, f"missing (v{version})"
    try:
        ds.upload_file(name=name, version=version, file_path=str(lw.EVAL_FILE))
        return name, f"registered (v{version})"
    except Exception as e:  # storage firewall / missing data-plane role: report, keep the agents
        return name, f"FAILED: {lw._trunc(e, 140)}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="report only; exit 1 if an agent is missing or out of date")
    ap.add_argument("--roles", help=f"comma-separated subset of {', '.join(ORDER)} (or full names)")
    ap.add_argument("--no-memory", action="store_true", help="build the tools/fabric agents without memory")
    ap.add_argument("--no-dataset", action="store_true", help="skip registering the livewell-eval dataset")
    args = ap.parse_args()

    names = demo_names()
    fabric = lw.fabric_enabled()
    rows, ok = [], True
    for role in pick_roles(args.roles):
        name = names[role]
        if role == "fabric" and not fabric:
            rows.append((name, "skipped (FABRIC_BRIDGE off)", "", "", ""))
            continue
        if args.check and role in ("tools", "fabric") and not args.no_memory:
            try:  # --check must not create the memory store
                lw.project().beta.memory_stores.get(MEMORY_STORE)
            except Exception:
                rows.append((name, "missing (memory store)", "", "", ""))
                ok = False
                continue
        kwargs, description = definition(role, memory=not args.no_memory)
        state, version = upsert(name, kwargs, description, check=args.check)
        ok &= state in ("in sync", "created", "updated")
        if version is not None:
            rows.append((name, state, f"v{version.version}", version.definition.model,
                         f"{lw.rai_policy_of(version) or 'deployment default'} | {tool_summary(version)}"))
        else:
            rows.append((name, state, "", kwargs["model"], ""))
        lw.say(f"[demo-agents] {name}: {state}")

    if not args.no_dataset and not args.roles:
        ds_name, ds_state = register_dataset(check=args.check)
        ok &= not ds_state.startswith(("missing", "FAILED"))
        rows.append((ds_name, ds_state.split(" (")[0] if len(ds_state) < 60 else "FAILED", "", "dataset", ds_state))
        lw.say(f"[demo-agents] dataset {ds_name}: {ds_state}")

    print()
    w = max(len(r[0]) for r in rows)
    print(f"  {'agent':<{w}}  {'state':<24} {'ver':<5} {'model':<14} guardrail | tools")
    for r in rows:
        print(f"  {r[0]:<{w}}  {r[1]:<24} {r[2]:<5} {r[3]:<14} {r[4]}")
    if not args.check:
        print("\n  Next: python scripts/smoke-test.py --demo-agents   (T-0 checks against these agents)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
