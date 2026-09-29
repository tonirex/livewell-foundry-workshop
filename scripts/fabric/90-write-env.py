#!/usr/bin/env python3
"""Step 90: write the Fabric IDs and URLs to the azd environment (.azure/<env>/.env).

Keys: FABRIC_WORKSPACE_ID, FABRIC_WORKSPACE_URL, FABRIC_LAKEHOUSE_ID, FABRIC_ONTOLOGY_ID,
FABRIC_GRAPH_MODEL_ID, FABRIC_DATA_AGENT_ID, FABRIC_DATA_AGENT_URL. Everything is looked up by name, so the
step is safe to re-run. Lab pages use names only; these IDs are for scripts (seed-attendees, render-values,
validate-narrative) and teardown.

  python scripts/fabric/90-write-env.py     (normally run by deploy.sh)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fabriclib as fl  # noqa: E402

PORTAL = "https://app.fabric.microsoft.com"


def azd_set(env: str, key: str, value: str) -> None:
    azd = shutil.which("azd") or "azd"
    proc = subprocess.run([azd, "env", "set", key, value, "-e", env], capture_output=True, text=True,
                          env={**os.environ, "AZURE_DEV_USER_AGENT": "microsoft_foundry_skill"})
    if proc.returncode != 0:
        raise SystemExit(f"azd env set {key} failed: {proc.stderr.strip()[:300]}")


def main() -> int:
    env = fl.env_name()
    n = fl.names(env)
    prefix = yaml.safe_load((fl.ROOT / "content" / "fabric" / "ontology.blueprint.yaml")
                            .read_text(encoding="utf-8"))["graph_refresh"]["graph_model_prefix"]
    fab = fl.Fabric()
    ws = fab.workspace_id(n["fabric_workspace"])
    if not ws:
        raise SystemExit(f"workspace \"{n['fabric_workspace']}\" not found: run deploy.sh")
    items = fab.items(ws)

    def find(item_type: str, name: str | None = None, starts: str | None = None) -> str:
        for i in items:
            if i.get("type") == item_type and (i.get("displayName") == name or
                                                (starts and i.get("displayName", "").startswith(starts))):
                return i["id"]
        return ""

    agent = find("DataAgent", n["data_agent"])
    values = {
        "FABRIC_WORKSPACE_ID": ws,
        "FABRIC_WORKSPACE_URL": f"{PORTAL}/groups/{ws}",
        "FABRIC_LAKEHOUSE_ID": find("Lakehouse", n["lakehouse"]),
        "FABRIC_ONTOLOGY_ID": find("Ontology", n["ontology"]),
        "FABRIC_GRAPH_MODEL_ID": find("GraphModel", starts=prefix),
        "FABRIC_DATA_AGENT_ID": agent,
        "FABRIC_DATA_AGENT_URL": f"{PORTAL}/groups/{ws}/aiskills/{agent}" if agent else "",
    }
    missing = [k for k, v in values.items() if not v]
    for key, value in values.items():
        if value:
            azd_set(env, key, value)
            fl.say(f"  PASS  {key}={value}")
    for key in missing:
        fl.say(f"  FAIL  {key}: item not found (run the earlier deploy steps)")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
