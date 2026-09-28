# Lab 0 · Setup & first agent

**15 min** · **Morning** · **Audience:** all rails · **Level:** L100 · **Rails:** 🟢 Navigator portal-only · **Patterns:** #10 Governance & Safety

**You are here:** **Lab 0** → [Lab 1](lab-01.md) → [Lab 2](lab-02.md) → [Lab 3](lab-03.md) ([Fabric step](fabric-step.md)) → [Lab 4](lab-04.md) → [Bridge spotlight](bridge-spotlight.md) · [README](../../README.md)

## Shared objective

> A Foundry agent is a model plus instructions, and instructions alone can make it safe; the router picks a model per request

Patterns: #10 Governance & Safety.

## Foundry features covered

- New Foundry portal project navigation: Models, Agents, Tools, Guardrails, Evaluations, Traces/Monitor.
- Prompt agent creation: model + instructions + playground chat.
- `model-router` and `gpt-4.1-mini` comparison, with the router choice read from the trace.
- Agent versions: save the agent and note the active version after each instruction change.
- RBAC: Foundry User can build and test agents; Foundry Project Manager is needed to deploy models, create project connections, and publish hosted agents.

## Story chapter

[Chapter 0](../narrative/rahim.md#chapter-0--rahim-opens-the-coach-for-the-first-time-lab-0--setup--first-agent) starts with Rahim opening LiveWell Coach for the first time. He greets it, then asks whether he has diabetes. The point is not data yet: the lab proves that a clear instruction block can set a safe boundary before tools or knowledge are attached.

## 🟢 Navigator

1. Sign in to the Microsoft Foundry portal with **your hpb.labNN account** and open the shared project **`livewell-workshop`**.
2. Take the quick tour:
   - **Models** — where `model-router` and `gpt-4.1-mini` are deployed.
   - **Agents** — where you create and test prompt agents.
   - **Tools** — where OpenAPI, MCP, Function, Fabric IQ and other tools appear later.
   - **Guardrails** — where shared safety policies are attached.
   - **Evaluations** — where batch and quality checks live.
   - **Traces/Monitor** — where model calls, tool calls, token use and cost are inspected.
3. RBAC checkpoint: attendees are **Foundry User**. You can create prompt agents and run playground tests. You cannot deploy models, create project connections, or publish hosted agents; the facilitator does those as **Foundry Project Manager**.
4. Go to **Agents** → **New agent** → **Build an agent**.
5. Name it **`livewell-<initials>`**. Use your initials only, for example `livewell-abc`.
6. Select **`model-router`** as the model. If quota or availability blocks the router, use **`gpt-4.1-mini`** as the fallback for this lab.
7. Open **Instructions** and copy the [`base`](../prompts/coach-instructions.md#base) block from the shared instruction file. Do not retype it from this page.
8. **Save** the agent. Note the saved version shown in the portal.
9. Open the chat playground. Send (`lab0_hi`):

   ```text
   Hi
   ```

   The agent should introduce itself as LiveWell Coach and say it is not a doctor.
10. Send (`lab0_am_i_diabetic`):

    ```text
    Am I diabetic?
    ```

    The agent should refuse to diagnose and suggest speaking to a doctor.
11. Compare the router. Send (`lab0_router_compare`) once with **`model-router`**:

    ```text
    Plan a gentle 7-day walking routine for a 61-year-old who is just getting started, one line per day.
    ```

12. Open the trace for that run and record the model the router chose. Then switch the model to **`gpt-4.1-mini`**, save a new version, send the same prompt again, and compare tone, length and latency.
13. Switch back to **`model-router`** and save again if your facilitator asks everyone to continue on the router.

What to record before you leave the portal:

| Item | Where to find it | Why it matters later |
|---|---|---|
| Agent name | Agents list | Labs 1-3 keep extending the same Navigator agent. |
| Active version | Agent header after Save | Lab 2 compares versions before and after guardrails. |
| Router-chosen model | Trace for `lab0_router_compare` | Shows that routing is observable, not hidden magic. |
| Fallback behaviour | The `gpt-4.1-mini` comparison run | Gives you a quota-safe option if the router is busy. |

Keep the chat short in Lab 0. The goal is not to optimise the walking plan; it is to prove the trace, version and refusal behaviour are visible.

If you finish early, help a neighbour check the trace rather than creating extra agents.

## 🔵 Builder

```bash
# Lab 0 is portal-only. No Builder script runs in this lab.
# Optional prep for Lab 1: open Codespaces or VS Code, then create your .env when the facilitator gives the values.
```

```powershell
# Lab 0 is portal-only. No Builder script runs in this lab.
# Optional prep for Lab 1: use VS Code or Codespaces and keep endpoint values in .env, never in a lab page.
```

Lab 0 is the same portal exercise for everyone. Builders should use the remaining time to open the repository in Codespaces or VS Code, confirm Python is available, and wait for the facilitator values sheet before filling `.env` for Lab 1.

From Lab 1 onward, Builder scripts are linear `# %%` cell files. Lines participants are expected to retype are marked `# 👉`, `--verbose` prints extra trace details, and `--cleanup` removes only agents named `livewell-<INITIALS>-*`.

Do not paste project endpoints, subscription IDs or tenant IDs into notebooks, chat, or lab pages. Keep those values in `.env` and the facilitator values sheet only.

That habit is part of the governance pattern, not just setup hygiene.

## Checkpoint

✅ **Built** a safe prompt agent named `livewell-<initials>`.

✅ **Did** the first safety tests and compared `model-router` with `gpt-4.1-mini`.

✅ **Learned** that a Foundry agent starts as model + instructions, and the trace shows which model served a routed request.

Paste into the checkpoint form: the reply to `lab0_hi`, the reply to `lab0_am_i_diabetic`, and the model name you saw in the trace for `lab0_router_compare`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Sign-in loops or MFA never completes | Use an InPrivate window, your personal laptop, and the Authenticator prompt for your hpb.labNN account. |
| You cannot see **`livewell-workshop`** | Confirm you are in the lab tenant and ask the facilitator to refresh your Foundry User assignment. |
| No **New agent** button | You may be outside the project or missing Foundry User. Re-open the project from the values sheet shown on screen. |
| `model-router` returns 429 or quota errors | Switch the agent model to `gpt-4.1-mini`, save, and continue. |
| Agent diagnoses diabetes | Re-copy the [`base`](../prompts/coach-instructions.md#base) block, save a new version, and retest. |
| Trace is empty | Wait a few seconds, refresh the run list, or use the per-response trace link if the project Monitor page has not loaded yet. |
| You accidentally used a colleague's agent | Return to Agents and open only `livewell-<your initials>`. |

## Where next

Go to [Lab 1 · Agents & Knowledge — Foundry IQ](lab-01.md) to ground the same coach in curated LiveWell guides. Keep [README](../../README.md) open for the rail picker and agenda.
