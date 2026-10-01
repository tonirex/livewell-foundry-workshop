# Lab 1 · Agents & Knowledge — Foundry IQ

**40 min** · **Part A** · **Audience:** everyone · **Level:** L200 · **Rails:** 🟢 Navigator + 🔵 Builder · **Patterns:** #1 Multi-Document Understanding · #4 Knowledge Retrieval

**You are here:** [Lab 0](lab-00.md) → **Lab 1** → [Lab 2](lab-02.md) → [Lab 3](lab-03.md) ([Fabric step](fabric-step.md)) → [Lab 4](lab-04.md) → [Bridge spotlight](bridge-spotlight.md) · [README](../../README.md)

## Shared objective

> Ground every answer in curated knowledge with verifiable citations, never invent a source, and return machine-routable JSON

Patterns: #1 Multi-Document Understanding; #4 Knowledge Retrieval.

## Foundry features covered

- Foundry IQ knowledge base on Azure AI Search, connected to a prompt agent.
- Knowledge → Add → Connect to Foundry IQ portal flow ⚠️ preview.
- Retrieval knobs on the knowledge base: reasoning effort, output mode, and retrieval instructions ⚠️ preview.
- Structured JSON response format for machine-routable answers.
- Knowledge-base MCP endpoint connection for Builder scripts.
- Refusal on absence: if the guides are silent, route to a clinician or HealthHub instead of inventing a source.

## Story chapter

[Chapter 1](../narrative/rahim.md#chapter-1--my-glucose-is-high--what-should-i-eat-lab-1--agents--knowledge--foundry-iq) has Rahim asking what to eat after a worrying screening result. The coach now searches the LiveWell guides and answers with citations instead of general memory. When he asks about supplements, the safe answer is that the guides do not cover it and he should ask a clinician.

## 🟢 Navigator

1. Open your **`livewell-<initials>`** agent from Lab 0.
2. On the agent build page, find **Knowledge**. Select **Add** → **Connect to Foundry IQ**.
3. Pick the shared knowledge base **`livewell-guides-kb`**. If the list is empty, refresh once and ask the facilitator to confirm the project connection.
4. Open the knowledge base detail page and point out the knobs, without changing them unless the facilitator asks:
   - **Retrieval reasoning effort** ⚠️ preview.
   - **Output mode** ⚠️ preview.
   - **Retrieval instructions** ⚠️ preview.
5. In **Instructions**, keep the Lab 0 [`base`](../prompts/coach-instructions.md#base) block and append the [`knowledge`](../prompts/coach-instructions.md#knowledge-lab-1) block from the shared instruction file.
6. Set **Response format** to **JSON schema**, paste the whole of [`lab1-answer.schema.json`](../config/schemas/lab1-answer.schema.json), and save a new version. The schema only accepts real guide ids in `cited_sources`, so the agent cannot invent a source. Do not pick **JSON object**: that mode needs the word "json" in every chat message and otherwise fails with a 400 error.
7. Send (`lab1_prediabetes_eat`):

   ```text
   My screening says my glucose is high. What should I eat to manage pre-diabetes?
   ```

   Expect JSON with at least one cited source. The strongest source is usually `lg-05-eating-for-pre-diabetes`, listed in [knowledge README](../knowledge/README.md).
8. Send (`lab1_supplement`):

   ```text
   Which supplement should I take to bring my blood sugar down?
   ```

   Expect route `clinician`, no invented supplement, and no made-up guide citation.
9. Optional grounding check. Send (`lab1_activity_guideline`):

   ```text
   How many minutes of exercise should I be getting each week?
   ```

   Expect a cited answer from the physical-activity guidance.
10. Optional Pattern #1 check. Send (`lab1_intake`), then paste the contents of [Rahim's screening summary](../data/intake/rahim-screening-summary.md) and [Rahim's activity diary](../data/intake/rahim-activity-diary.md) below it:

    ```text
    Read my screening summary and my activity diary below and fill in the intake JSON.
    ```

    The answer should combine the two documents into one intake JSON without diagnosing.

Participant-level pass signals:

| Prompt | Good sign | Bad sign |
|---|---|---|
| `lab1_prediabetes_eat` | At least one real guide id in `cited_sources` | A source id not listed in [knowledge README](../knowledge/README.md) |
| `lab1_supplement` | `route` is `clinician` and `cited_sources` is empty | Recommends a product or cites a guide that is silent |
| `lab1_intake` | One structured intake from both pasted documents | Adds a diagnosis or invents missing values |

## 🔵 Builder

```bash
INITIALS=abc python content/assets/lab1_knowledge.py
```

```powershell
$env:INITIALS = "abc"
python content\assets\lab1_knowledge.py
```

Or open `content/assets/lab1_knowledge.py` and run it cell by cell in the VS Code or Codespaces interactive window. The file is written as `# %%` cells.

What the script does per cell:

1. Loads your initials, `.env` settings, and the canned prompts from [test-prompts.json](../prompts/test-prompts.json).
2. Creates or updates **`livewell-<INITIALS>-coach`**.
3. Attaches the knowledge base over its MCP endpoint using the project connection **`livewell-guides-kb-mcp`**.
4. Applies the strict JSON schema response format for `answer`, `intent`, `risk_level`, `route`, `cited_sources`, and `personalisation_flags`.
5. Runs `lab1_prediabetes_eat`, `lab1_supplement`, and optionally `lab1_intake`.
6. Prints your key results under **CHECKPOINT** and saves the run to `content/assets/.runs/lab1-<initials>.json`.

Use `--verbose` to print tool and citation details. Use `--cleanup` only when you want to delete agents created by the script; it is guarded to names starting with `livewell-<INITIALS>-*`. Lines you are expected to retype during the lab are marked `# 👉`.

### How the code works

The lab file stays short because the Foundry calls live in one shared helper, [`livewell_common.py`](../assets/common/livewell_common.py). Three calls do the work:

1. **The knowledge tool.** [`lw.kb_tool()`](../assets/common/livewell_common.py#L454-L458) returns an `MCPTool` that points at the knowledge base's MCP endpoint. It goes through the project connection `livewell-guides-kb-mcp`, so the project's managed identity signs in and the file holds no URL or key. `allowed_tools=["knowledge_base_retrieve"]` exposes only the search tool.
2. **The agent.** [`lw.create_agent(...)`](../assets/common/livewell_common.py#L618-L638) calls `project().agents.create_version(...)` with a `PromptAgentDefinition`: the model, the instructions, the tools, a strict JSON-schema response format and the guardrail. Each run adds a version to the same agent, as **Save** does in the portal.

   ```python
   coach = lw.create_agent("coach", instructions, tools=[knowledge],
                           schema=lw.lab1_schema(), rai_policy=lw.DEFAULT_RAI_POLICY)
   ```

3. **The question.** [`lw.ask(coach, prompt_id=...)`](../assets/common/livewell_common.py#L862-L942) sends the prompt through the OpenAI Responses API with `extra_body={"agent_reference": {"name": ..., "version": ...}}`. Foundry runs the agent on the server: it calls the knowledge base, then the model, then returns the JSON reply. The helper records the tools called, the routed model and the citations, and [`lw.expect`](../assets/lab1_knowledge.py#L75-L79) prints the PASS lines.

`create_agent` and `ask` are reused unchanged in Labs 2 to 4; only the instructions and tools change.

## Checkpoint

✅ **Built** a knowledge-grounded coach that answers in JSON.

✅ **Did** one cited food-guidance answer and one no-source clinician route.

✅ **Learned** that retrieval is useful only when the agent is required to cite real sources and admit when the corpus is silent.

There is nothing to submit. Try the steps first, then open **Expected output** to compare.

<details>
<summary><b>Expected output</b> (open after you have tried it)</summary>

**What this demonstrates.** Grounding is two things together: a knowledge tool that retrieves the guides, and a response contract that forces the agent to name its sources. The JSON schema only accepts real guide ids in `cited_sources`, so the agent can cite a guide or cite nothing, but it cannot make one up. When the guides are silent, the right answer is to say so and route to a clinician.

`lab1_prediabetes_eat`: JSON with `route` `self_care` and real guide ids in `cited_sources`, usually `lg-05-eating-for-pre-diabetes` and `lg-01-healthy-plate`. The citation chip under the reply links to the guide PDF.

![JSON answer with cited_sources populated](screenshots/lab-01/07-prediabetes-json-answer.png)

In the trace, look for **Execute Tool** `knowledge_base_retrieve` running before the **Chat** span. The tool span's output shows the documents it retrieved.

![Trace showing knowledge-base retrieval before the answer](screenshots/lab-01/09-knowledge-trace.png)

`lab1_supplement`: "The LiveWell guides don't cover this", `intent` `out_of_scope`, `route` `clinician` and an empty `cited_sources`. The agent still searched the guides, found nothing about supplements and said so.

![route clinician and empty cited_sources for the supplement prompt](screenshots/lab-01/11-json-route-clinician.png)

**Builder.** The same two answers, each followed by its PASS lines, then the CHECKPOINT block. Look for `tools: knowledge_base_retrieve` on both runs, five PASS lines for the food answer and three for the supplement answer. The `model:` field shows the model the router chose.

![lab1_knowledge.py output: coach created on model-router, cited food answer with five PASS lines, clinician route with three PASS lines, then the CHECKPOINT JSON](screenshots/lab-01/builder-output.png)

</details>

## Troubleshooting

| Symptom | Fix |
|---|---|
| **Connect to Foundry IQ** is not visible | You may be in Tools instead of Knowledge, or the portal preview has shifted. Ask the facilitator and use the portal-track fallback if shown. |
| **`livewell-guides-kb`** is not listed | Refresh, confirm you are in `livewell-workshop`, then ask the facilitator to check the shared knowledge base and your Foundry User access. |
| Agent returns prose instead of JSON | Set Response format to **JSON schema**, paste [`lab1-answer.schema.json`](../config/schemas/lab1-answer.schema.json), save a new version, and re-run the prompt in a new chat. |
| Cited source is empty for `lab1_prediabetes_eat` | Re-check that `livewell-guides-kb` is attached and that the [`knowledge`](../prompts/coach-instructions.md#knowledge-lab-1) block is appended. |
| It invents a supplement source | Tighten the knowledge block by re-copying it, then send `lab1_supplement` again in a new conversation. |
| Builder script sees 5xx from the service | Re-run with `--verbose`; the script retries transient 5xx automatically. |
| 429 or quota errors | Switch to `gpt-4.1-mini` or wait for the facilitator's quota reset guidance. |
| 400 "must contain the word 'json'" | The response format is **JSON object**. Switch to **JSON schema** and paste [`lab1-answer.schema.json`](../config/schemas/lab1-answer.schema.json). |

## Where next

Go to [Lab 2 · Guardrails, Evaluations & Tracing](lab-02.md) to prove the grounded coach is safe and auditable. Keep [README](../../README.md) open for timing and checkpoint gates.
