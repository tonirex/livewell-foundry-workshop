# Lab 4 · Multi-agent & Hosted deploy

**30 min** · **Facilitator demo / Engineer appendix** · **Level:** L300 · **Rails:** 🟢 watch + 🔵 local orchestration · **Patterns:** #3 Workflow Orchestration · #9 Collaboration Between Specialists · #10 Governance & Safety

**You are here:** [Lab 0](lab-00.md) → [Lab 1](lab-01.md) → [Lab 2](lab-02.md) → [Lab 3](lab-03.md) ([Fabric step](fabric-step.md)) → **Lab 4** → [Bridge spotlight](bridge-spotlight.md) · [README](../../README.md)

## Shared objective

> From playground to production: the same agent behind two doors (portal for people, endpoint for systems), governed by the same policy

Patterns: #3 Workflow Orchestration; #9 Collaboration Between Specialists; #10 Governance & Safety.

## Foundry features covered

- Microsoft Agent Framework sequential + handoff orchestration: Coach → Nutrition → Activity.
- Programme-Insights specialist **`livewell-<INITIALS>-insights`** using the Fabric tool for officer questions.
- Agent versioning and trace comparison across playground and hosted runs.
- Hosted deploy via Foundry Toolkit for VS Code or `azd ai agent`.
- `rai_config` on the hosted agent so the same RAI policy protects the endpoint.
- Hosted-agent tracing in Foundry and Application Insights.
- RBAC ceiling: participants are Foundry User, so publishing is facilitator-only.

## Story chapter

[Chapter 4](../narrative/rahim.md#chapter-4--livewell-goes-live-lab-4--multi-agent--hosted-deploy) moves LiveWell Coach from playground behaviour to a hosted endpoint. Rahim's week-planning request flows through Nutrition and Activity specialists before returning a single JSON reply. Mei's programme question goes to a Programme-Insights specialist, showing the same agent family serving citizen and officer seats through governed routes.

## 🟢 Navigator

Watch the facilitator demo; here is what to look for:

1. The facilitator opens the local Agent Framework orchestration and points out the sequence: **Coach → Nutrition → Activity**.
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

   Look for a Fabric-routed aggregate answer grouped by programme and no resident-level detail.
5. Watch the hosted deploy path. The facilitator uses Foundry Toolkit for VS Code or `azd ai agent`, attaches the RAI policy with `rai_config`, and deploys **`livewell-workshop-hosted`**.
6. Smoke test the hosted endpoint with Python or curl. The endpoint is read from the values sheet shown on screen and is never written into this page.
7. Open the hosted-agent trace and compare it with the playground trace.
8. Note why participants cannot publish: Foundry User can build and test; Foundry Project Manager is required for hosted publish.

> The Foundry portal **Workflows** item is not used in this workshop because it is retiring on **1 Dec 2026**. Multi-agent orchestration is shown with Microsoft Agent Framework, connected agents and function tools instead.

Demo map:

| Moment | What to watch | Why it matters |
|---|---|---|
| Local orchestration | Nutrition runs before Activity | Sequential handoff is explicit, not implied. |
| Programme-Insights | Officer prompt uses Fabric | Specialist routing keeps citizen and officer data paths separate. |
| Hosted deploy | `rai_config` references the RAI policy | Governance follows the agent into production. |
| Smoke test | JSON plus citation returns from endpoint | Systems can consume the same governed behaviour. |
| Hosted trace | Tool spans and policy spans appear | Operations can audit the deployed agent. |

## 🔵 Builder

```bash
INITIALS=abc python content/assets/lab4_multiagent.py
```

```powershell
$env:INITIALS = "abc"
python content\assets\lab4_multiagent.py
```

Or open `content/assets/lab4_multiagent.py` and run it cell by cell in VS Code or Codespaces. The Agent Framework orchestration runs locally for everyone; hosted deploy remains facilitator-only.

What the script does per cell:

1. Loads the same prompts and instruction blocks used in prior labs.
2. Creates local Nutrition and Activity specialists, then runs a sequential + handoff orchestration.
3. Creates **`livewell-<INITIALS>-insights`** when Fabric is enabled and routes officer questions to the Fabric tool.
4. Runs `lab4_week_plan_handoff` and prints the handoff trace.
5. Optionally demonstrates the hosted-agent scaffold in `content/assets/hosted-agent-example/`; this is code span only because the files arrive in Phase 4.
6. Shows where `rai_config` attaches **`livewell-guardrails`** for hosted deployment.

Use `--verbose` for orchestration trace details. Use `--cleanup` to delete only `livewell-<INITIALS>-*` agents. Retype lines are marked `# 👉`.

Engineer appendix notes:

- The scaffold in `content/assets/hosted-agent-example/` is intentionally separate from participant lab code.
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
| Hosted deploy fails because policy is missing | Confirm **`livewell-guardrails`** exists and the hosted scaffold uses `rai_config`. |
| Trace shows only one specialist | Re-run the Agent Framework script and check the handoff rule; the week-plan prompt should require both Nutrition and Activity. |
| Programme-Insights calls the knowledge base instead of Fabric | Re-copy the fabric routing block in the specialist instructions and confirm the Fabric tool is attached. |
| Endpoint smoke test returns prose | Check the response-format contract in the hosted scaffold and re-run the smoke prompt. |
| 429 or quota errors | Use `gpt-4.1-mini` for the demo or reduce concurrent participant runs. |
| Foundry Toolkit cannot see the project | Confirm sign-in with the lab account and use the project values shown on screen, not personal subscription settings. |

## Where next

Close with [Bridge spotlight · Two IQs, one agent](bridge-spotlight.md), or revisit the optional [Fabric step](fabric-step.md) if the bridge was skipped earlier. Keep [README](../../README.md) open for post-workshop resources.
