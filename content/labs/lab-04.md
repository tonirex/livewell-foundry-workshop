# Lab 4 · Multi-agent & Hosted deploy

**30 min** · **Facilitator demo / Engineer appendix** · **Level:** L300 · **Rails:** 🟢 watch + 🔵 local orchestration · **Patterns:** #3 Workflow Orchestration · #9 Collaboration Between Specialists · #10 Governance & Safety

**You are here:** [Lab 0](lab-00.md) → [Lab 1](lab-01.md) → [Lab 2](lab-02.md) → [Lab 3](lab-03.md) ([Fabric step](fabric-step.md)) → **Lab 4** → [Bridge spotlight](bridge-spotlight.md) · [README](../../README.md)

## Shared objective

> From playground to production: the same agent behind two doors (portal for people, endpoint for systems), governed by the same policy

Patterns: #3 Workflow Orchestration; #9 Collaboration Between Specialists; #10 Governance & Safety.

## Foundry features covered

- Microsoft Agent Framework sequential and handoff orchestration: Nutrition → Activity → Coach, and Coach → Nutrition → Activity.
- Programme-Insights specialist **`livewell-<INITIALS>-insights`** using the Fabric tool for officer questions.
- Agent versioning and trace comparison across local and hosted runs.
- Hosted deploy with `azd deploy` (code deploy: Foundry builds the container; no Docker needed).
- `rai_config` on the hosted agent so the same RAI policy protects the endpoint.
- Hosted-agent tracing in Foundry and Application Insights.
- RBAC ceiling: participants are Foundry User, so publishing is facilitator-only. The hosted agent runs as its own Entra agent identity with Foundry User on the project.

## Story chapter

[Chapter 4](../narrative/rahim.md#chapter-4--livewell-goes-live-lab-4--multi-agent--hosted-deploy) moves LiveWell Coach from playground behaviour to a hosted endpoint. Rahim's week-planning request flows through Nutrition and Activity specialists before returning a single JSON reply. Mei's programme question goes to a Programme-Insights specialist, showing the same agent family serving citizen and officer seats through governed routes.

## 🟢 Navigator

Watch the facilitator demo; here is what to look for:

1. The facilitator opens the local Agent Framework orchestration and points out the two shapes: a **sequential** team (Nutrition → Activity → Coach) and a **handoff** team where the Coach triages (Coach → Nutrition → Activity).
2. The facilitator adds or shows **`livewell-<INITIALS>-insights`**, the Programme-Insights specialist that uses the Fabric tool for programme-level questions.
3. Send (`lab4_week_plan_handoff`):

   ```text
   Plan my week: what to eat for my glucose, and one indoor morning activity near Woodlands.
   ```

   Look for Nutrition then Activity in the trace, followed by valid JSON with at least one citation.
4. Send (`lab4_q_programmes_disengaged`) to the Programme-Insights specialist:

   ```text
   Which programmes have the most disengaged residents enrolled?
   ```

   Look for a Fabric-routed aggregate answer grouped by programme and no resident-level detail. The reference
   answer puts **<!--ref:q_programmes_disengaged_enrolled.top_programme-->Healthier SG<!--/ref-->** first
   (<!--ref:q_programmes_disengaged_enrolled.top_disengaged_enrolled-->82<!--/ref--> disengaged residents enrolled). The top programmes
   are close, so ±1 rank is a pass.
5. Watch the hosted deploy path. The facilitator runs `azd deploy livewell-workshop-hosted`: Foundry builds the sequential team from `content/assets/hosted-agent-example/`, then a postdeploy step gives the agent's identity Foundry User on the project and attaches **`livewell-guardrails`** with `rai_config`.
6. Smoke test the hosted endpoint (`azd ai agent invoke`, or section 7 of the Builder script). The endpoint is read from the values sheet shown on screen and is never written into this page. Then a blocklisted prompt: it must come back blocked.
7. Open the hosted-agent trace and compare it with the playground trace.
8. Note why participants cannot publish: Foundry User can build and test; Foundry Project Manager is required for hosted publish.

> The Foundry portal **Workflows** item is not used in this workshop because it is retiring on **1 Dec 2026**. Multi-agent orchestration is shown with Microsoft Agent Framework, connected agents and function tools instead.

Demo map:

| Moment | What to watch | Why it matters |
|---|---|---|
| Local orchestration | Nutrition runs before Activity | Sequential handoff is explicit, not implied. |
| Programme-Insights | Officer prompt uses Fabric | Specialist routing keeps citizen and officer data paths separate. |
| Hosted deploy | `rai_config` references the RAI policy; the agent identity gets a role | Governance and least privilege follow the agent into production. |
| Smoke test | JSON plus citation returns from endpoint; the blocklisted prompt is blocked | Systems can consume the same governed behaviour. |
| Hosted trace | Tool spans and policy spans appear | Operations can audit the deployed agent. |

## 🔵 Builder

```bash
INITIALS=abc python content/assets/lab4_multiagent.py
```

```powershell
$env:INITIALS = "abc"
python content\assets\lab4_multiagent.py
```

Or open `content/assets/lab4_multiagent.py` and run it cell by cell in VS Code or Codespaces. The Agent Framework orchestration runs on your machine and calls the project's model deployments, so `livewell-guardrails` still applies. Hosted deploy remains facilitator-only.

What the script does per section:

1. **Request.** Reads your profile from the activities app (`/profile/me`) as a one-line summary and puts it in front of `lab4_week_plan_handoff`. The resident_id never enters the conversation.
2. **Client and tools.** One Agent Framework client for the project, plus the Lab 3 tools: the knowledge-base MCP endpoint and `find_activities` (never `register_interest`).
3. **Specialists.** Nutrition and Activity, each with its instruction block. A small `text_only` middleware passes earlier answers on as plain text.
4. **Sequential team.** Nutrition → Activity → Coach; the Coach merges both answers into the Lab 3 evidence JSON. Prints the trace and checks JSON, a real guide citation, an indoor morning activity and no resident_id.
5. **Handoff team** (skip with `--no-handoff`). The Coach triages and hands off to Nutrition, which hands off to Activity. Checks the route and that both specialists answered.
6. **Programme-Insights** (only with `--fabric`, when the facilitator confirms `FABRIC_BRIDGE=true`). Creates **`livewell-<INITIALS>-insights`** with the Fabric tool and asks `lab4_q_programmes_disengaged`; checks the top programme against the reference answer.
7. **Hosted agent.** Once the facilitator has deployed **`livewell-workshop-hosted`**, sends it the same week-plan prompt on its own endpoint and checks that its guardrail is **`livewell-guardrails`**, the reply is evidence JSON with a real guide, and no resident_id appears. Before the deploy it just says "not deployed yet".
8. **Checkpoint.** Prints the paste block and saves the run to `content/assets/.runs/`.

Use `--verbose` for each agent's full answer. Use `--cleanup` to delete only `livewell-<INITIALS>-*` agents (the hosted agent has a protected name and is never deleted). Retype lines are marked `# 👉`.

Engineer appendix notes:

- `content/assets/hosted-agent-example/` packages section 4 as a hosted agent: `main.py` (about 100 lines), `livewell.json` (instructions, tools and schema, generated from the same prompt blocks) and a pinned `requirements.txt`. Its [README](../assets/hosted-agent-example/README.md) covers deploy, smoke test, local runs and troubleshooting.
- Hosted agents answer only on their own endpoint, `{project endpoint}/agents/<name>/endpoint/protocols/openai`; the project's Responses endpoint with an `agent_reference` is refused.
- The facilitator reads endpoint values from the values sheet or environment only.
- Participants can still run the Agent Framework orchestration locally without hosted publish rights.
- Any production channel setup is outside the participant checkpoint.
- Keep local orchestration output for comparison with the hosted trace.

## Checkpoint

✅ **Built** or watched a multi-agent orchestration with governed handoffs.

✅ **Did** a hosted-agent smoke test if you are the facilitator, or inspected the live trace as a participant.

✅ **Learned** what changes when an agent moves from playground to endpoint: RBAC, policy attachment, versioning and operational traces.

Paste into the checkpoint form: the JSON output for `lab4_week_plan_handoff` from the facilitator smoke test, or the trace summary showing Nutrition then Activity. If the Programme-Insights demo ran, paste the grouped programme answer for `lab4_q_programmes_disengaged`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Participant cannot publish | Expected. Hosted publish needs Foundry Project Manager; watch the facilitator demo. |
| Section 7 says the hosted agent is not deployed yet | Expected before the facilitator demo; re-run the cell afterwards. |
| Section 7: 424 `session_not_ready` | The hosted agent is cold-starting; wait a minute and re-run. If it persists, the facilitator checks the container log (hosted-agent README). |
| Section 7: guardrail check fails | Facilitator: `python scripts/hosted-postdeploy.py --verify` re-attaches **`livewell-guardrails`** and checks a blocked prompt. |
| Trace shows only one specialist | Re-run the Agent Framework script and check the handoff rule; the week-plan prompt should require both Nutrition and Activity. |
| `Workflow is already running` | One request at a time per workflow; re-run the cell. |
| Programme-Insights calls the knowledge base instead of Fabric | Re-copy the fabric routing block in the specialist instructions and confirm the Fabric tool is attached. |
| Endpoint smoke test returns prose | The hosted agent's `livewell.json` is stale: the facilitator runs `python scripts/gen-schemas.py` and redeploys. |
| 429 or quota errors | Use `gpt-4.1-mini` for the demo or reduce concurrent participant runs. |

## Where next

Close with [Bridge spotlight · Two IQs, one agent](bridge-spotlight.md), or revisit the optional [Fabric step](fabric-step.md) if the bridge was skipped earlier. Keep [README](../../README.md) open for post-workshop resources.
