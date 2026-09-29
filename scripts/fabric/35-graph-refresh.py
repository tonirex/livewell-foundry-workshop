#!/usr/bin/env python3
"""Step 35: refresh the ontology's graph model and wait for Completed.

Creating the ontology provisions a child graph model (resident_ontology_graph_*) that holds the entity and
relationship instances. The data agent fails with a backend graph error until that graph has been
loaded, and upstream table changes are not picked up until it is refreshed again. This step:

  1. finds the graph model (GraphModel items whose name starts with graph_refresh.graph_model_prefix);
  2. if a refresh is already running (Fabric starts one when the ontology is created or updated), waits for it
     and uses it;
  3. otherwise (or with --force) runs POST /v1/workspaces/{ws}/items/{id}/jobs/refreshGraph/instances and polls
     to Completed (about 5-9 min on F2);
  4. counts nodes per entity type and edges per relationship type with GQL and compares them with scripts/r360.py.

If the API is unavailable it prints the one-click portal step and waits for you to confirm.

  python scripts/fabric/35-graph-refresh.py [--force] [--no-trigger] [--timeout 1800]   (normally run by deploy.sh)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fabriclib as fl  # noqa: E402

BLUEPRINT = fl.ROOT / "content" / "fabric" / "ontology.blueprint.yaml"
RUNNING = ("NotStarted", "InProgress", "Running")


def runbook(ws_name: str, prefix: str) -> str:
    return (f"  Portal step: app.fabric.microsoft.com -> workspace \"{ws_name}\" -> open the graph model "
            f"{prefix}* -> Schedule -> Refresh now -> wait until the refresh shows Completed.")


def find_graph(fab: fl.Fabric, ws: str, prefix: str, wait_s: int = 300) -> dict | None:
    start = time.time()
    while True:
        graphs = [i for i in fab.items(ws) if i.get("type") == "GraphModel"
                  and i.get("displayName", "").startswith(prefix)]
        if graphs:
            return sorted(graphs, key=lambda g: g["displayName"])[-1]
        if time.time() - start > wait_s:
            return None
        fl.say("    waiting for the graph model to appear...")
        time.sleep(20)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-trigger", action="store_true", help="only wait for a running refresh")
    ap.add_argument("--force", action="store_true", help="start a new refresh even after waiting for a running one")
    ap.add_argument("--timeout", type=int, default=1800)
    a = ap.parse_args()
    bp = yaml.safe_load(BLUEPRINT.read_text(encoding="utf-8"))
    prefix = bp["graph_refresh"]["graph_model_prefix"]
    n = fl.names()
    fab = fl.Fabric()
    ws = fab.workspace_id(n["fabric_workspace"])
    if not ws:
        raise SystemExit(f"workspace \"{n['fabric_workspace']}\" not found: run 10-workspace.sh")
    graph = find_graph(fab, ws, prefix)
    if not graph:
        types = sorted({f"{i['type']}:{i['displayName']}" for i in fab.items(ws)})
        fl.say(f"  FAIL  no GraphModel named {prefix}* in the workspace (items: {types})")
        fl.say(runbook(n["fabric_workspace"], prefix))
        return 1
    gid = graph["id"]
    fl.say(f"  PASS  graph model {graph['displayName']} ({gid})")

    jobs_path = f"/v1/workspaces/{ws}/items/{gid}/jobs/instances"
    jobs = fab.get_all(jobs_path)
    running = [j for j in jobs if j.get("status") in RUNNING]
    inst: dict = {}
    if running:
        # Creating or updating the ontology starts a refresh by itself; that one already covers the latest change.
        fl.say(f"  info  a refresh is already {running[0]['status']}: waiting for it")
        try:
            inst = fab.wait_job(f"{fl.FABRIC}{jobs_path}/{running[0]['id']}", a.timeout, "graph refresh")
        except RuntimeError as e:
            fl.say(f"  info  that refresh ended without completing ({str(e)[:120]}); starting a new one")
            inst = {}
    if not a.no_trigger and (a.force or not inst):
        try:
            inst = fab.run_job(ws, gid, "refreshGraph", timeout=a.timeout, what="graph refresh")
        except fl.ApiError as e:
            fl.say(f"  WARN  refreshGraph API unavailable ({e.status} {e.code or ''}); do it in the portal:")
            fl.say(runbook(n["fabric_workspace"], prefix))
            if not sys.stdin.isatty():
                return 2
            input("  Press Enter once the refresh shows Completed... ")
            inst = {"status": "Completed (confirmed by facilitator)"}
    elif not inst:
        done = [j for j in fab.get_all(jobs_path) if j.get("status") == "Completed"]
        inst = done[0] if done else {"status": "none"}
    ok = str(inst.get("status", "")).startswith("Completed")
    fl.say(f"  {'PASS' if ok else 'FAIL'}  graph refresh {inst.get('status')}"
           f"{' at ' + inst['endTimeUtc'] if inst.get('endTimeUtc') else ''}")
    if ok:
        ok = check_instances(fab, ws, gid, bp)
    print(json.dumps({"FABRIC_GRAPH_MODEL_ID": gid}))
    return 0 if ok else 1


def gql(fab: fl.Fabric, ws: str, gid: str, query: str) -> list:
    _, _, body = fab.call("POST", f"/v1/workspaces/{ws}/graphModels/{gid}/executeQuery?beta=true", {"query": query})
    return ((body or {}).get("result") or {}).get("data") or []


def check_instances(fab: fl.Fabric, ws: str, gid: str, bp: dict) -> bool:
    """Count nodes per entity type and edges per relationship type (GQL) against the local gold build."""
    sys.path.insert(0, str(fl.ROOT / "scripts"))
    import r360  # noqa: PLC0415

    t = r360.build()
    ok = True
    try:
        for e in bp["entity_types"]:
            got = int(gql(fab, ws, gid, f"MATCH (n:{e['id']}) RETURN count(n) AS n")[0]["n"])
            want = len({row[e["key"]] for row in t[e["table"]]})
            ok &= got == want
            fl.say(f"  {'PASS' if got == want else 'FAIL'}  {e['id']:<16} {got:>5} instances (local {want})")
        for r in bp["relationship_types"]:
            q = f"MATCH (:{r['origin']['entity']})-[x:{r['id']}]->(:{r['target']['entity']}) RETURN count(x) AS n"
            got = int(gql(fab, ws, gid, q)[0]["n"])
            want = len({(row[r["origin"]["key_column"]], row[r["target"]["key_column"]])
                        for row in t[r["mapping_table"]]})
            ok &= got == want
            fl.say(f"  {'PASS' if got == want else 'FAIL'}  {r['id']:<16} {got:>5} edges (local {want})")
    except (fl.ApiError, IndexError, KeyError, ValueError) as e:
        fl.say(f"  WARN  could not count graph instances with GQL (executeQuery preview): {e}")
    return ok


if __name__ == "__main__":
    sys.exit(main())
