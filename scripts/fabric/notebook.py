#!/usr/bin/env python3
"""Notebook helpers for 20-lakehouse-load.sh.

  python scripts/fabric/notebook.py prepare --ws-id <ws> --lh-id <lh> --out <dir>
      Writes <dir>/load_resident360.Notebook/ (notebook-content.ipynb + .platform) for `fab import`,
      with lh_resident360 injected as the default lakehouse. The committed notebook has no IDs.

  python scripts/fabric/notebook.py run-config --ws-id <ws> --lh-id <lh>
      Prints the RunNotebook configuration JSON (default lakehouse) for `fab job run -C`.

  python scripts/fabric/notebook.py verify --ws-id <ws> --lh-id <lh>
      Lists the lakehouse Delta tables, reads Files/export/load_summary.json from OneLake and checks
      the counts, Rahim and the headline reference answer against the local build (scripts/r360.py).
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import fabriclib as fl  # noqa: E402

NOTEBOOK = fl.ROOT / "content" / "assets" / "load_resident360.ipynb"
NB_NAME = "load_resident360"


def prepare(ws: str, lh: str, lh_name: str, out: Path) -> Path:
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    nb = copy.deepcopy(nb)
    nb.setdefault("metadata", {})["dependencies"] = {
        "lakehouse": {
            "default_lakehouse": lh,
            "default_lakehouse_name": lh_name,
            "default_lakehouse_workspace_id": ws,
            "known_lakehouses": [{"id": lh}],
        }
    }
    folder = out / f"{NB_NAME}.Notebook"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "notebook-content.ipynb").write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    platform = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Notebook", "displayName": NB_NAME,
                     "description": "Loads the minimal LiveWell Resident 360 into lh_resident360 (synthetic data)."},
        "config": {"version": "2.0", "logicalId": str(uuid.UUID(int=0))},  # the "not in git" logicalId
    }
    (folder / ".platform").write_text(json.dumps(platform, indent=2), encoding="utf-8")
    return folder


def run_config(ws: str, lh: str, lh_name: str) -> dict:
    return {"defaultLakehouse": {"name": lh_name, "id": lh, "workspaceId": ws}, "useStarterPool": True}


def verify(ws: str, lh: str) -> int:
    import r360

    fab = fl.Fabric()
    failures = 0
    tables = {t["name"]: t for t in fab.get_all(f"/v1/workspaces/{ws}/lakehouses/{lh}/tables")}
    local = r360.build()
    raw = fab.onelake_read(ws, lh, "Files/export/load_summary.json")
    if raw is None:
        print("  FAIL  Files/export/load_summary.json not found: did the notebook run?")
        return 1
    summary = json.loads(raw.decode("utf-8"))
    for name, rows in local.items():
        got = summary["counts"].get(name)
        present = name in tables
        status = "PASS" if (present and got == len(rows)) else "FAIL"
        failures += status == "FAIL"
        fmt = tables.get(name, {}).get("format", "missing")
        print(f"  {status}  table {name:26s} {str(got):>6s} rows (local {len(rows)}), {fmt}")
    want_rahim = r360.rahim_facts(local)
    if summary.get("rahim") != json.loads(json.dumps(want_rahim, default=str)):
        failures += 1
        print("  FAIL  Rahim differs between Fabric and the local build")
    else:
        print(f"  PASS  Rahim {r360.load_rahim()['resident_id']}: {want_rahim['region']} / "
              f"{want_rahim['age_band']} / risk {want_rahim['screening_risk']} / disengaged {want_rahim['is_disengaged']}")
    ref_local = r360.reference_answers(local)["q_disengaged_regions"]["top_region"]
    ref_fabric = summary["reference_answers"]["q_disengaged_regions"]["top_region"]
    ok = ref_local == ref_fabric
    failures += not ok
    print(f"  {'PASS' if ok else 'FAIL'}  top disengaged region: Fabric {ref_fabric}, local {ref_local}")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["prepare", "run-config", "verify"])
    ap.add_argument("--ws-id", required=True)
    ap.add_argument("--lh-id", required=True)
    ap.add_argument("--lh-name", default="lh_resident360")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.mode == "prepare":
        print(prepare(a.ws_id, a.lh_id, a.lh_name, Path(a.out)))
        return 0
    if a.mode == "run-config":
        print(json.dumps(run_config(a.ws_id, a.lh_id, a.lh_name)))
        return 0
    return verify(a.ws_id, a.lh_id)


if __name__ == "__main__":
    sys.exit(main())
