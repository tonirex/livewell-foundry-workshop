"""Shared helpers for scripts/fabric/*.py: Fabric REST (long-running operations, jobs), OneLake reads,
item lookups by display name, and definition parts. Standard library + pyyaml only.

Auth is the caller's Azure CLI user token (`az login`), the same identity as `fab auth login`.
Names come from content/config/workshop.yaml (`names.*`) with <env> substituted.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))

from azrest import ApiError, az_token  # noqa: E402
import wsconfig  # noqa: E402

FABRIC = "https://api.fabric.microsoft.com"
ONELAKE = "https://onelake.dfs.fabric.microsoft.com"


def say(msg: str) -> None:
    print(msg, flush=True)


def env_name() -> str:
    env = os.environ.get("AZURE_ENV_NAME", "")
    if not env:
        raise SystemExit("AZURE_ENV_NAME is not set: run through scripts/fabric/deploy.sh <env>")
    return env


def names(env: str | None = None) -> dict:
    return wsconfig.load(env or env_name())["names"]


class Fabric:
    """Fabric REST with LRO + job polling. `call` returns (status, headers, body)."""

    def __init__(self, tenant: str | None = None):
        self._tenant = tenant or os.environ.get("AZURE_TENANT_ID") or None
        self.token = az_token(FABRIC, self._tenant)
        self._storage_token: str | None = None

    # -- raw ---------------------------------------------------------------------------------
    def call(self, method: str, path: str, body: object | None = None):
        url = path if path.startswith("http") else FABRIC + path
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(8):
            req = urllib.request.Request(url, data=data, method=method)
            req.add_header("Authorization", "Bearer " + self.token)
            req.add_header("Content-Type", "application/json")
            try:
                with urllib.request.urlopen(req, timeout=180) as resp:
                    return resp.status, dict(resp.headers), _parse(resp.read())
            except urllib.error.HTTPError as e:
                raw = e.read()
                if e.code in (429, 500, 502, 503, 504) and attempt < 7:
                    wait = int(e.headers.get("Retry-After", "0") or 0) or min(60, 2 ** attempt)
                    say(f"    (HTTP {e.code}, retrying in {wait}s)")
                    time.sleep(wait)
                    continue
                if e.code == 404:
                    return 404, dict(e.headers), _parse(raw)
                raise ApiError(e.code, raw.decode("utf-8", "replace"), url) from None
        raise RuntimeError(f"gave up after retries: {method} {url}")

    def get(self, path: str):
        status, _, body = self.call("GET", path)
        return None if status == 404 else body

    def get_all(self, path: str) -> list:
        out, url = [], path
        while url:
            page = self.get(url) or {}
            out += page.get("value", page.get("data", []))
            url = page.get("continuationUri")
        return out

    # -- long-running operations / jobs ----------------------------------------------------------
    def lro(self, method: str, path: str, body: object | None = None, what: str = "", timeout: int = 900):
        """POST that may answer 202; polls /v1/operations/{id} and returns the result body (or {})."""
        status, headers, result = self.call(method, path, body)
        if status != 202:
            return result
        op = _h(headers, "x-ms-operation-id")
        poll = f"{FABRIC}/v1/operations/{op}" if op else _h(headers, "Location")
        start, wait = time.time(), int(_h(headers, "Retry-After") or 5)
        while True:
            time.sleep(max(2, min(wait, 20)))
            _, headers2, state = self.call("GET", poll)
            s = (state or {}).get("status", "")
            if s in ("Succeeded", "Completed"):
                break
            if s in ("Failed", "Cancelled", "Canceled"):
                raise RuntimeError(f"{what or path}: operation {s}: {json.dumps(state)[:1200]}")
            if time.time() - start > timeout:
                raise TimeoutError(f"{what or path}: still {s} after {timeout}s")
            wait = int(_h(headers2, "Retry-After") or wait)
        if op:
            st, _, res = self.call("GET", f"{FABRIC}/v1/operations/{op}/result")
            if st not in (400, 404) and res:
                return res
        return result or {}

    def run_job(self, ws: str, item: str, job_type: str, body: object | None = None,
                timeout: int = 1800, what: str = "") -> dict:
        """Run an on-demand item job and wait for Completed. Returns the final job instance."""
        status, headers, _ = self.call("POST", f"/v1/workspaces/{ws}/items/{item}/jobs/{job_type}/instances",
                                       body or {})
        loc = _h(headers, "Location")
        if status not in (200, 202) or not loc:
            raise RuntimeError(f"{what or job_type}: unexpected HTTP {status} (no Location header)")
        return self.wait_job(loc, timeout, what or job_type)

    def wait_job(self, loc: str, timeout: int, what: str) -> dict:
        start, last = time.time(), ""
        while True:
            time.sleep(10)
            inst = self.get(loc) or {}
            s = inst.get("status", "")
            if s != last:
                say(f"    {what}: {s} ({int(time.time() - start)}s)")
                last = s
            if s == "Completed":
                return inst
            if s in ("Failed", "Cancelled", "Deduped"):
                raise RuntimeError(f"{what}: {s}: {json.dumps(inst.get('failureReason'))[:1200]}")
            if time.time() - start > timeout:
                raise TimeoutError(f"{what}: still {s} after {timeout}s")

    # -- lookups -------------------------------------------------------------------------------
    def workspace_id(self, display_name: str) -> str | None:
        for w in self.get_all("/v1/workspaces"):
            if w.get("displayName") == display_name:
                return w["id"]
        return None

    def items(self, ws: str, item_type: str | None = None) -> list:
        q = f"?type={urllib.parse.quote(item_type)}" if item_type else ""
        return self.get_all(f"/v1/workspaces/{ws}/items{q}")

    def item_id(self, ws: str, item_type: str, display_name: str) -> str | None:
        for it in self.items(ws, item_type):
            if it.get("displayName") == display_name:
                return it["id"]
        return None

    def definition(self, ws: str, item: str, fmt: str | None = None) -> dict:
        q = f"?format={fmt}" if fmt else ""
        res = self.lro("POST", f"/v1/workspaces/{ws}/items/{item}/getDefinition{q}", what="getDefinition")
        return decode_parts(res.get("definition", {}))

    # -- OneLake -------------------------------------------------------------------------------
    def storage_token(self) -> str:
        if not self._storage_token:
            self._storage_token = az_token("https://storage.azure.com", self._tenant)
        return self._storage_token

    def onelake_read(self, ws: str, item: str, rel_path: str) -> bytes | None:
        url = f"{ONELAKE}/{ws}/{item}/{urllib.parse.quote(rel_path)}"
        req = urllib.request.Request(url, method="GET")
        req.add_header("Authorization", "Bearer " + self.storage_token())
        req.add_header("x-ms-version", "2023-11-03")
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise ApiError(e.code, e.read().decode("utf-8", "replace"), url) from None


def _h(headers: dict, name: str) -> str:
    for k, v in (headers or {}).items():
        if k.lower() == name.lower():
            return v
    return ""


def _parse(raw: bytes):
    if not raw or not raw.strip():
        return {}
    try:
        return json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        return {"_raw": raw.decode("utf-8", "replace")}


def part(path: str, content: object) -> dict:
    data = content if isinstance(content, (bytes, str)) else json.dumps(content, indent=2)
    if isinstance(data, str):
        data = data.encode("utf-8")
    return {"path": path, "payload": base64.b64encode(data).decode("ascii"), "payloadType": "InlineBase64"}


def decode_parts(definition: dict) -> dict:
    out = {}
    for p in (definition or {}).get("parts", []):
        raw = base64.b64decode(p["payload"])
        try:
            out[p["path"]] = json.loads(raw)
        except ValueError:
            out[p["path"]] = raw.decode("utf-8", "replace")
    return out


def stable_id(name: str) -> str:
    """Deterministic positive int64 (as a string) per name: ontology entity/property/relationship IDs."""
    h = int.from_bytes(hashlib.sha256(name.encode("utf-8")).digest()[:8], "big")
    return str(10**12 + h % (9 * 10**12))


def stable_guid(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "livewell-foundry-workshop/" + name))
