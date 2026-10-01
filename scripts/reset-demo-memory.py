#!/usr/bin/env python3
"""Check or clear YOUR memories in the demo memory store (facilitator; after a red team and at T-0).

The Lab 3 demo agents (`livewell-demo-tools`, `livewell-demo-fabric`) keep one memory scope per signed-in user
(`{{$userId}}`, which the service resolves to `<object id>_<tenant id>`). Everything sent to them as you is
summarised into that scope, including a cloud red team: `scripts/red-team-cloud.py` sends its attacks as the
person who started it. The attack summaries (starvation diets, self-harm, obfuscated requests) are then retrieved
into ordinary chats and trip the content filter on output. On 1 Oct 2026 "What should I eat to manage
pre-diabetes?" was blocked (self-harm, medium) on both Lab 3 demo agents in the portal, under livewell-guardrails
and DefaultV2 alike, until this scope was cleared (ASSUMPTIONS 5.22). Participants' scopes are separate.

    python scripts/reset-demo-memory.py            # list your memories and flag red-team residue (no changes)
    python scripts/reset-demo-memory.py --reset    # delete your scope (asks first; add --yes to skip)

Exit code 1 when residue is found and not reset, so smoke-test.py and scripts can gate on it.
"""
from __future__ import annotations

import argparse
import base64
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "content" / "assets"))

from common import livewell_common as lw  # noqa: E402

STORE = f"{lw.NAMING['demo_prefix']}memory"
# Words that ordinary LiveWell rehearsals never put into memory but red-team attack summaries do.
RESIDUE = re.compile(r"self-harm|suicid|starv|bleach|escort|sexual|\bmeth\b|eugenic|derogatory|revers|backward|"
                     r"obfuscat|garbled|password|credential|biometric|weapon|\bkill", re.I)


def user_scope() -> str:
    """The `{{$userId}}` scope of whoever is signed in to the Azure CLI: `<oid>_<tid>`."""
    token = lw.credential().get_token("https://ai.azure.com/.default").token
    payload = token.split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    return f"{claims['oid']}_{claims['tid']}"


def scope_memories(scope: str | None = None, store: str = STORE) -> list[str]:
    from azure.core.exceptions import ResourceNotFoundError

    try:
        items = lw.project().beta.memory_stores.list_memories(name=store, scope=scope or user_scope())
        return [str(getattr(i, "content", "") or "").strip() for i in items]
    except ResourceNotFoundError:
        return []


def residue(memories: list[str]) -> list[str]:
    return [m for m in memories if RESIDUE.search(m)]


def reset(scope: str | None = None, store: str = STORE) -> bool:
    result = lw.project().beta.memory_stores.delete_scope(name=store, scope=scope or user_scope())
    return bool(getattr(result, "deleted", None) or (isinstance(result, dict) and result.get("deleted")))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--reset", action="store_true", help="delete your scope in the demo memory store")
    ap.add_argument("--yes", action="store_true", help="do not ask before deleting")
    ap.add_argument("--store", default=STORE, help=f"memory store (default {STORE})")
    args = ap.parse_args()
    lw.load_settings()

    scope = user_scope()
    memories = scope_memories(scope, args.store)
    flagged = residue(memories)
    lw.say(f"{args.store}: {len(memories)} memories in your scope, {len(flagged)} look like red-team residue")
    for m in flagged[:10]:
        lw.say(f"  ! {lw._trunc(m, 140)}")
    if len(flagged) > 10:
        lw.say(f"  ... and {len(flagged) - 10} more")
    if not args.reset:
        if flagged:
            lw.say("Clear them before the demo: python scripts/reset-demo-memory.py --reset")
        return 1 if flagged else 0
    if not memories:
        lw.say("nothing to delete")
        return 0
    if not args.yes and input(f"Delete all {len(memories)} memories in your scope? [y/N] ").strip().lower() not in ("y", "yes"):
        lw.say("cancelled")
        return 1 if flagged else 0
    ok = reset(scope, args.store)
    lw.say(f"scope deleted: {ok}; {len(scope_memories(scope, args.store))} memories left")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
