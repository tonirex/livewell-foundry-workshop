#!/usr/bin/env python3
"""Ask the published Fabric data agent a question through its MCP endpoint (user token, stdlib only).

  python scripts/fabric/ask.py "Which regions have the highest share of disengaged residents?"
  python scripts/fabric/ask.py --json "..."        # machine-readable (used by validate-narrative.py)

Endpoint: https://api.fabric.microsoft.com/v1/mcp/workspaces/{ws}/dataagents/{id}/agent
(MCP over streamable HTTP: initialize -> tools/list -> tools/call; the agent is exposed as one tool).
Workspace and agent are looked up by name from workshop.yaml, or taken from FABRIC_WORKSPACE_ID /
FABRIC_DATA_AGENT_ID when set. Expect 30-90 s per question.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fabriclib as fl  # noqa: E402

PROTOCOL = "2025-06-18"


class Mcp:
    def __init__(self, url: str, token: str):
        self.url, self.token, self.session, self._id = url, token, None, 0

    def _post(self, payload: dict, timeout: int = 300):
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode(), method="POST")
        req.add_header("Authorization", "Bearer " + self.token)
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        req.add_header("MCP-Protocol-Version", PROTOCOL)
        if self.session:
            req.add_header("Mcp-Session-Id", self.session)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                self.session = resp.headers.get("Mcp-Session-Id") or self.session
                ctype = resp.headers.get("Content-Type", "")
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            raise fl.ApiError(e.code, e.read().decode("utf-8", "replace"), self.url) from None
        if not raw.strip() or "id" not in payload:
            return None  # notifications are acknowledged with 202 and no JSON-RPC body
        if "text/event-stream" in ctype:
            msgs = [json.loads(line[5:].strip()) for line in raw.splitlines()
                    if line.startswith("data:") and line[5:].strip()]
            for m in msgs:
                if m.get("id") == payload.get("id"):
                    return m
            return msgs[-1] if msgs else None
        return json.loads(raw)

    def request(self, method: str, params: dict | None = None, timeout: int = 300) -> dict:
        self._id += 1
        msg = self._post({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}, timeout)
        if msg is None:
            raise RuntimeError(f"{method}: empty response")
        if "error" in msg:
            raise RuntimeError(f"{method}: {json.dumps(msg['error'])[:600]}")
        return msg.get("result", {})

    def notify(self, method: str) -> None:
        self._post({"jsonrpc": "2.0", "method": method})


def resolve() -> tuple[str, str]:
    ws, agent = os.environ.get("FABRIC_WORKSPACE_ID", ""), os.environ.get("FABRIC_DATA_AGENT_ID", "")
    if ws and agent:
        return ws, agent
    n = fl.names()
    fab = fl.Fabric()
    ws = ws or fab.workspace_id(n["fabric_workspace"]) or ""
    agent = agent or (fab.item_id(ws, "DataAgent", n["data_agent"]) if ws else "") or ""
    if not (ws and agent):
        raise SystemExit("workspace or data agent not found: run scripts/fabric/deploy.sh")
    return ws, agent


def ask(question: str, ws: str, agent: str, token: str | None = None) -> dict:
    token = token or fl.az_token(fl.FABRIC, os.environ.get("AZURE_TENANT_ID") or None)
    mcp = Mcp(f"{fl.FABRIC}/v1/mcp/workspaces/{ws}/dataagents/{agent}/agent", token)
    mcp.request("initialize", {"protocolVersion": PROTOCOL, "capabilities": {},
                               "clientInfo": {"name": "livewell-ask", "version": "1.0"}})
    mcp.notify("notifications/initialized")
    tools = mcp.request("tools/list").get("tools", [])
    if not tools:
        raise RuntimeError("the data agent MCP server lists no tools (is the agent published?)")
    tool = tools[0]
    schema = tool.get("inputSchema") or {}
    props = schema.get("properties") or {}
    arg = next((k for k in (schema.get("required") or []) if (props.get(k) or {}).get("type") == "string"),
               next((k for k, v in props.items() if v.get("type") == "string"), "question"))
    start = time.time()
    result = mcp.request("tools/call", {"name": tool["name"], "arguments": {arg: question}}, timeout=600)
    text = "\n".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
    # The agent prefixes this when its query failed (e.g. no entity types selected), then may invent numbers.
    failed = "content here that I can't work with" in text or "content here that I can’t work with" in text
    return {"question": question, "tool": tool["name"], "argument": arg, "answer": text,
            "is_error": bool(result.get("isError")) or failed, "seconds": round(time.time() - start, 1)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    ws, agent = resolve()
    res = ask(a.question, ws, agent)
    if a.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"Q: {res['question']}\n({res['tool']}, {res['seconds']} s)\n\n{res['answer']}")
    if res["is_error"]:
        print("\nERROR: the data agent could not query the ontology; any numbers above are not grounded. "
              "Re-run scripts/fabric/40-data-agent.py (selects entity types) and 35-graph-refresh.py.",
              file=sys.stderr)
    return 1 if res["is_error"] else 0


if __name__ == "__main__":
    sys.exit(main())
