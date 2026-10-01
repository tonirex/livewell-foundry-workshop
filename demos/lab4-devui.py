#!/usr/bin/env python3
"""Lab 4 facilitator demo: watch the Agent Framework orchestration run, agent by agent, in DevUI.

`lab4_multiagent.py` prints the route as text. This opens the same two workflows in Agent Framework DevUI, a local
web page that draws each workflow graph, lights up the agent that is running, and streams every tool call and
answer into the chat. The Traces panel shows the OpenTelemetry spans of each run.

    python demos/lab4-devui.py                 # http://127.0.0.1:8090: "LiveWell sequential" and "LiveWell hand-off"
    python demos/lab4-devui.py --mermaid       # print the WorkflowViz graphs (the diagrams in lab-04.md) and exit
    python demos/lab4-devui.py --port 8091 --no-browser
    python demos/lab4-devui.py --capture       # run both workflows headless and refresh the lab-04 DevUI screenshots

It prints the request to paste into the chat box (your profile summary + `lab4_week_plan_handoff`). The agents
mirror `content/assets/lab4_multiagent.py` sections 3-5 (same instruction blocks, tools and builders) and, like
them, call the project's deployments directly under the deployment guardrail (Microsoft.DefaultV2). DevUI binds to
127.0.0.1 only. Needs `pip install -r requirements-demos.txt` (agent-framework-devui), your az login with Foundry
User and the azd env (AZURE_ENV_NAME) or a filled .env. Stop it with Ctrl+C.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "content" / "assets"))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from common import livewell_common as lw  # noqa: E402

from agent_framework import Agent, Message, WorkflowViz, agent_middleware  # noqa: E402
from agent_framework.orchestrations import HandoffBuilder, SequentialBuilder  # noqa: E402


@agent_middleware
async def text_only(context, call_next):
    """Same as lab4_multiagent.py section 3: earlier answers reach each agent as plain text."""
    context.messages[:] = [Message(m.role, [m.text], author_name=m.author_name) for m in context.messages if m.text]
    await call_next()


def build(client, knowledge, find_activities):
    def team(*extra: str) -> tuple[Agent, Agent]:
        common = {"middleware": [text_only], "require_per_service_call_history_persistence": True}
        nutrition = Agent(client, lw.load_instructions("nutrition", *extra), name="nutrition",
                          description="Meal suggestions grounded in the LiveWell guides", tools=[knowledge], **common)
        activity = Agent(client, lw.load_instructions("activity", *extra), name="activity",
                         description="Safe activities and community activities", tools=[knowledge, find_activities],
                         **common)
        return nutrition, activity

    nutrition, activity = team()
    coach = Agent(client, lw.load_instructions("base", "safety", "merge"), name="coach",
                  description="LiveWell Coach: merges the specialists' answers", middleware=[text_only],
                  default_options=lw.af_json_format(lw.evidence_schema(), "livewell_evidence"))
    sequential = SequentialBuilder(participants=[nutrition, activity, coach], output_from="all").build()
    sequential.name, sequential.description = "LiveWell sequential", "Nutrition -> Activity -> Coach (Lab 4 section 4)"

    nutrition, activity = team("handoff")
    triage = Agent(client, lw.load_instructions("base", "handoff"), name="coach",
                   description="LiveWell Coach: triage only", middleware=[text_only],
                   require_per_service_call_history_persistence=True)
    handoff = (HandoffBuilder(name="livewell_handoff", participants=[triage, nutrition, activity],
                              termination_condition=lambda conv: any(m.author_name == "activity" and m.text
                                                                     for m in conv if m.role == "assistant"))
               .with_start_agent(triage)
               .add_handoff(triage, [nutrition, activity])
               .add_handoff(nutrition, [activity])
               .add_handoff(activity, [triage])
               .with_autonomous_mode(agents=[nutrition], turn_limits={"nutrition": 1}, prompts={
                   "nutrition": "If the resident also asked about activity, hand off to the Activity specialist now."})
               .build())
    handoff.name, handoff.description = "LiveWell hand-off", "Coach triages -> Nutrition -> Activity (Lab 4 section 5)"
    return sequential, handoff


# workflow -> (screenshot, side-panel tab to show)
SHOTS = {"LiveWell sequential": ("10-devui-sequential.png", "Events"),
         "LiveWell hand-off": ("11-devui-handoff.png", "Tools")}


def capture(port: int, request: str) -> int:
    """Start DevUI in a child process, run each workflow from its Configure & Run form and screenshot the result."""
    from playwright.sync_api import sync_playwright

    out = ROOT / "content" / "labs" / "screenshots" / "lab-04"
    base = f"http://127.0.0.1:{port}"
    server = subprocess.Popen([sys.executable, __file__, "--port", str(port), "--no-browser"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(120):
            try:
                urllib.request.urlopen(f"{base}/health", timeout=2)
                break
            except OSError:
                time.sleep(1)
        else:
            lw.say("DevUI did not start")
            return 1
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1600, "height": 950})
            for name, (file, tab) in SHOTS.items():
                page.goto(base, wait_until="networkidle")
                page.get_by_role("button", name="LiveWell").first.click()
                page.get_by_role("menuitem", name=name).click()
                page.get_by_role("button", name="Configure & Run").click()
                page.get_by_placeholder("Enter role").fill("user")
                page.get_by_placeholder("Enter contents").fill(request)
                page.get_by_role("button", name="Run Workflow").click()
                page.get_by_role("button", name="Run Again").wait_for(timeout=300_000)
                page.get_by_role("tab", name=tab).click()
                page.wait_for_timeout(1500)
                page.screenshot(path=str(out / file))
                lw.say(f"saved {(out / file).relative_to(ROOT)}")
            browser.close()
        return 0
    finally:
        server.terminate()
        server.wait(timeout=30)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--mermaid", action="store_true", help="print the two workflow graphs as Mermaid and exit")
    ap.add_argument("--no-browser", action="store_true", help="do not open the browser")
    ap.add_argument("--capture", action="store_true", help="refresh the lab-04 DevUI screenshots (needs Playwright)")
    args = ap.parse_args()
    lw.load_settings()
    if args.capture:
        return capture(args.port, f"{lw.profile_summary(lw.get_citizen_profile('me'))}\n\n"
                                  f"{lw.prompt_text('lab4_week_plan_handoff')}")

    client = lw.af_client()
    workflows = build(client, lw.af_kb_tool(client), lw.af_activities_tool(client))
    if args.mermaid:
        for wf in workflows:
            print(f"%% {wf.name}\n{WorkflowViz(wf).to_mermaid()}")
        return 0
    try:
        from agent_framework.devui import serve
    except ImportError:
        lw.say("DevUI is not installed: python -m pip install -r requirements-demos.txt")
        return 1

    lw.warm_activities()
    request = f"{lw.profile_summary(lw.get_citizen_profile('me'))}\n\n{lw.prompt_text('lab4_week_plan_handoff')}"
    lw.heading("Paste this into the DevUI chat box")
    print(request)
    lw.say(f"\nDevUI on http://127.0.0.1:{args.port} (Ctrl+C to stop). Pick a workflow at the top left.")
    serve(entities=list(workflows), port=args.port, host="127.0.0.1", auto_open=not args.no_browser,
          instrumentation_enabled=True, auth_enabled=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
