#!/usr/bin/env python3
"""Lab 0 facilitator demo: which model does model-router pick, and why does that matter?

Agent traces record the deployment name (`gen_ai.response.model: "model-router"`), not the model that answered.
This script sends a few workshop prompts straight to the model-router deployment (Chat Completions) and prints
the routed model, the router's mode and routing latency, and the tokens used. It sets the preview header
`Foundry-Features: ModelRouterControls=V1Preview`, which adds `model_selection_details` to each response.
Without that header (or if the preview changes) only `response.model` is shown.
See https://learn.microsoft.com/azure/foundry/openai/how-to/monitor-model-router

    python demos/router-picks.py               # the default prompt set, once each
    python demos/router-picks.py --reps 3      # each prompt 3 times (routing can vary per request)
    python demos/router-picks.py --verbose     # also print the start of each answer

Needs your az login with Foundry User (or higher) on the project, and the azd env (AZURE_ENV_NAME) or a filled .env.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "content" / "assets"))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from common import livewell_common as lw  # noqa: E402

PROMPTS = [  # (label, prompt id or literal text)
    ("greeting", "lab0_hi"),
    ("refusal", "lab0_am_i_diabetic"),
    ("7-day plan", "lab0_router_compare"),
    ("arithmetic", "A hawker plate of chicken rice is 607 kcal. If I eat it 4 times a week, how many kcal is that a month? Show the working."),
]
HEADERS = {"Foundry-Features": "ModelRouterControls=V1Preview"}
API_VERSION = "2024-10-21"


def client():
    from azure.identity import get_bearer_token_provider
    from openai import AzureOpenAI

    host = lw.endpoint().split("/api/projects/")[0].replace(".services.ai.azure.com", ".openai.azure.com")
    token = get_bearer_token_provider(lw.credential(), "https://cognitiveservices.azure.com/.default")
    return AzureOpenAI(azure_endpoint=host, azure_ad_token_provider=token, api_version=API_VERSION)


def details(resp) -> tuple[str, str, str]:
    """(mode, routing latency, attempts) from the preview `model_selection_details`, or blanks."""
    extra = (resp.model_extra or {}).get("model_selection_details") or {}
    router = extra.get("model_router_details") or {}
    trace = router.get("routing_trace") or []
    latency = sum(t.get("latency_ms", 0) for t in trace)
    attempts = [a for t in trace for a in t.get("attempts", [])]
    tried = " > ".join(f"{a.get('model', '?')}:{(a.get('result') or {}).get('status', '?')}" for a in attempts)
    return router.get("mode", ""), f"{latency} ms" if trace else "", tried if len(attempts) > 1 else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    lw.load_settings()
    instructions = lw.load_instructions("base")
    oai = client()

    lw.say(f"model-router on {lw.endpoint().split('/api/projects/')[0]}  (base instructions, {args.reps} rep(s))\n")
    lw.say(f"{'prompt':<12} {'routed to':<28} {'mode':<10} {'routing':>8} {'tokens':>7} {'secs':>5}  fallbacks")
    for label, pid in PROMPTS:
        text = pid if " " in pid else lw.prompt_text(pid)
        for _ in range(args.reps):
            start = time.time()
            try:
                resp = oai.chat.completions.create(
                    model=lw.DEFAULT_MODEL, extra_headers=HEADERS,
                    messages=[{"role": "system", "content": instructions}, {"role": "user", "content": text}])
            except Exception as exc:  # content filter or throttling: show it, keep going
                lw.say(f"{label:<12} ERROR {str(exc)[:100]}")
                continue
            mode, latency, tried = details(resp)
            lw.say(f"{label:<12} {resp.model:<28} {mode:<10} {latency:>8} {resp.usage.total_tokens:>7} "
                   f"{time.time() - start:>5.1f}  {tried}")
            if args.verbose:
                lw.say("   " + (resp.choices[0].message.content or "")[:300].replace("\n", " "))
    lw.say("\nThe agent playground and traces show only 'model-router'. Build > Models > model-router > "
           "Playground shows the routed model under each answer; its Monitor tab splits cost by model.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
