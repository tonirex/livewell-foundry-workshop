#!/usr/bin/env python3
"""Step 30: render content/fabric/ontology.blueprint.yaml into a Fabric ontology definition and create
resident_ontology (4 entity types, 4 relationship types) in the workshop workspace.

Modelled on Microsoft Learn mslearn-fabric Lab 28 `setup-ontology.ipynb`: generic items endpoint,
`LakehouseTable` NonTimeSeries data bindings (every entity's first and only binding is static), and one
Contextualization per relationship over the table whose rows are the links.

Idempotent: IDs are deterministic (hash of the blueprint names), so a re-run produces the same definition.
If the ontology exists its definition is updated in place (the item ID the data agent uses stays the same);
`--recreate` deletes and creates it instead.

  python scripts/fabric/30-ontology.py [--dry-run] [--recreate]     (normally run by deploy.sh)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fabriclib as fl  # noqa: E402

BLUEPRINT = fl.ROOT / "content" / "fabric" / "ontology.blueprint.yaml"


def render(bp: dict, ws: str, lh: str) -> tuple[list[dict], dict]:
    onto = bp["ontology"]["name"]
    schema = (bp["ontology"].get("schema") or "").strip()
    ents, keyprop, parts = {}, {}, []

    def table_props(table: str) -> dict:
        props = {"sourceType": "LakehouseTable", "workspaceId": ws, "itemId": lh, "sourceTableName": table}
        if schema:
            props["sourceSchema"] = schema
        return props

    for e in bp["entity_types"]:
        eid = fl.stable_id(f"{onto}/entity/{e['id']}")
        pids = {p["name"]: fl.stable_id(f"{onto}/entity/{e['id']}/{p['name']}") for p in e["properties"]}
        ents[e["id"]] = eid
        keyprop[e["id"]] = pids[e["key"]]
        definition = {
            "id": eid, "namespace": "usertypes", "namespaceType": "Custom", "name": e["id"],
            "visibility": "Visible", "baseEntityTypeId": None,
            "entityIdParts": [pids[e["key"]]],
            "displayNamePropertyId": pids[e.get("display_name_property") or e["key"]],
            "properties": [{"id": pids[p["name"]], "name": p["name"], "valueType": p["type"],
                            "redefines": None, "baseTypeNamespaceType": None} for p in e["properties"]],
            "timeseriesProperties": [],
        }
        binding = {
            "id": fl.stable_guid(f"{onto}/binding/{e['id']}"),
            "dataBindingConfiguration": {
                "dataBindingType": "NonTimeSeries",
                "propertyBindings": [{"sourceColumnName": p["column"], "targetPropertyId": pids[p["name"]]}
                                     for p in e["properties"]],
                "sourceTableProperties": table_props(e["table"]),
            },
        }
        parts += [fl.part(f"EntityTypes/{eid}/definition.json", definition),
                  fl.part(f"EntityTypes/{eid}/DataBindings/{binding['id']}.json", binding)]

    for r in bp["relationship_types"]:
        rid = fl.stable_id(f"{onto}/rel/{r['id']}")
        src, tgt = r["origin"], r["target"]
        definition = {"id": rid, "namespace": "usertypes", "namespaceType": "Custom", "name": r["id"],
                      "source": {"entityTypeId": ents[src["entity"]]},
                      "target": {"entityTypeId": ents[tgt["entity"]]}}
        ctx = {
            "id": fl.stable_guid(f"{onto}/ctx/{r['id']}"),
            "dataBindingTable": table_props(r["mapping_table"]),
            "sourceKeyRefBindings": [{"sourceColumnName": src["key_column"], "targetPropertyId": keyprop[src["entity"]]}],
            "targetKeyRefBindings": [{"sourceColumnName": tgt["key_column"], "targetPropertyId": keyprop[tgt["entity"]]}],
        }
        parts += [fl.part(f"RelationshipTypes/{rid}/definition.json", definition),
                  fl.part(f"RelationshipTypes/{rid}/Contextualizations/{ctx['id']}.json", ctx)]

    head = [fl.part(".platform", {"metadata": {"type": "Ontology", "displayName": onto}}),
            fl.part("definition.json", {})]
    return head + parts, ents


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="render and print the parts; no Fabric calls")
    ap.add_argument("--recreate", action="store_true", help="delete the ontology first (new item ID)")
    a = ap.parse_args()
    bp = yaml.safe_load(BLUEPRINT.read_text(encoding="utf-8"))
    onto = bp["ontology"]["name"]

    if a.dry_run:
        parts, _ = render(bp, "<workspace-id>", "<lakehouse-id>")
        for p in parts:
            print(p["path"])
        print(f"{len(parts)} parts")
        return 0

    n = fl.names()
    fab = fl.Fabric()
    ws = fab.workspace_id(n["fabric_workspace"])
    if not ws:
        raise SystemExit(f"workspace \"{n['fabric_workspace']}\" not found: run 10-workspace.sh")
    lh = fab.item_id(ws, "Lakehouse", bp["ontology"]["lakehouse"])
    if not lh:
        raise SystemExit(f"lakehouse {bp['ontology']['lakehouse']} not found: run 20-lakehouse-load.sh")
    tables = {t["name"] for t in fab.get_all(f"/v1/workspaces/{ws}/lakehouses/{lh}/tables")}
    need = {e["table"] for e in bp["entity_types"]} | {r["mapping_table"] for r in bp["relationship_types"]}
    if need - tables:
        raise SystemExit(f"lakehouse tables missing: {sorted(need - tables)}: run 20-lakehouse-load.sh")
    fl.say(f"  PASS  source tables present: {', '.join(sorted(need))}")

    parts, _ = render(bp, ws, lh)
    definition = {"parts": parts}
    existing = fab.item_id(ws, "Ontology", onto)
    if existing and a.recreate:
        fab.call("DELETE", f"/v1/workspaces/{ws}/items/{existing}")
        fl.say(f"  deleted existing {onto} ({existing})")
        existing = None
    if existing:
        fab.lro("POST", f"/v1/workspaces/{ws}/items/{existing}/updateDefinition", {"definition": definition},
                what=f"update {onto}")
        oid = existing
        fl.say(f"  PASS  {onto} definition updated ({len(parts)} parts)")
    else:
        res = fab.lro("POST", f"/v1/workspaces/{ws}/items",
                      {"displayName": onto, "type": "Ontology", "description": bp["ontology"]["description"],
                       "definition": definition}, what=f"create {onto}")
        oid = (res or {}).get("id") or fab.item_id(ws, "Ontology", onto)
        fl.say(f"  PASS  {onto} created ({len(parts)} parts)")
    if not oid:
        raise SystemExit(f"{onto} not found after create")

    got = fab.definition(ws, oid)
    n_ent = sum(1 for p in got if p.startswith("EntityTypes/") and p.endswith("/definition.json"))
    n_rel = sum(1 for p in got if p.startswith("RelationshipTypes/") and p.endswith("/definition.json"))
    n_bind = sum(1 for p in got if "/DataBindings/" in p)
    n_ctx = sum(1 for p in got if "/Contextualizations/" in p)
    ok = (n_ent, n_rel) == (len(bp["entity_types"]), len(bp["relationship_types"]))
    fl.say(f"  {'PASS' if ok else 'FAIL'}  {onto}: {n_ent} entity types, {n_rel} relationship types, "
           f"{n_bind} data bindings, {n_ctx} contextualizations")
    graphs = [i for i in fab.items(ws) if i.get("type") in ("GraphModel", "Graph")]
    for g in graphs:
        fl.say(f"  info  graph model: {g['displayName']} ({g['type']}, {g['id']})")
    print(json.dumps({"FABRIC_ONTOLOGY_ID": oid}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
