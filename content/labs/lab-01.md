# Lab 1 · Agents & Knowledge — Foundry IQ

**40 min** · **Part A** · **Audience:** everyone · **Level:** L200 · **Rails:** 🟢 Navigator + 🔵 Builder · **Patterns:** #4 Knowledge Retrieval · #1 Multi-Document Understanding (optional step)

**You are here:** [Lab 0](lab-00.md) → **Lab 1** → [Lab 2](lab-02.md) → [Lab 3](lab-03.md) ([Fabric step](fabric-step.md)) → [Lab 4](lab-04.md) → [Bridge spotlight](bridge-spotlight.md) · [README](../../README.md)

## Shared objective

> Ground every answer in curated knowledge with verifiable citations, never invent a source, and return machine-routable JSON

Patterns: #4 Knowledge Retrieval; #1 Multi-Document Understanding in the optional intake step (Navigator step 10, Builder `--intake`).

## Foundry features covered

- Foundry IQ knowledge base on Azure AI Search, connected to a prompt agent.
- Knowledge → Add → Connect to Foundry IQ portal flow ⚠️ preview.
- How Foundry IQ works and the knowledge-base settings (retrieval reasoning effort, output mode, retrieval instructions), in the optional **Explore further** panel ⚠️ preview.
- Structured JSON response format for machine-routable answers.
- Knowledge-base MCP endpoint connection for Builder scripts.
- Refusal on absence: if the guides are silent, route to a clinician or HealthHub instead of inventing a source.

## Story chapter

[Chapter 1](../narrative/rahim.md#chapter-1--my-glucose-is-high--what-should-i-eat-lab-1--agents--knowledge--foundry-iq) has Rahim asking what to eat after a worrying screening result. The coach now searches the LiveWell guides and answers with citations instead of general memory. When he asks about supplements, the safe answer is that the guides do not cover it and he should ask a clinician.

## 🟢 Navigator

1. Open your **`livewell-<initials>`** agent from Lab 0.
2. On the agent build page, find **Knowledge**. Select **Add** → **Connect to Foundry IQ**.
3. Pick the shared knowledge base **`livewell-guides-kb`**. If the list is empty, refresh once and ask the facilitator to confirm the project connection.
4. Select **Connect**. `livewell-guides-kb` now shows under **Knowledge** on your agent.

   > **Note:** The facilitator built this knowledge base before the workshop and everyone shares it. You don't create a knowledge base or an index, and the attach panel doesn't show its settings. To see what sits behind it, open **Explore further** after the pass signals below.
5. In **Instructions**, keep the Lab 0 [`base`](../prompts/coach-instructions.md#base) block and append the [`knowledge`](../prompts/coach-instructions.md#knowledge-lab-1) block from the shared instruction file.
6. Set the response format. It is in the **Parameters** panel, not on the main build page:
   1. Select the **Parameters** icon (the sliders icon) just to the right of the **Model** dropdown at the top of the build page.
   2. Set **Text format** to **JSON Schema**.
   3. In the schema editor, replace the example with the whole of [`lab1-answer.schema.json`](../config/schemas/lab1-answer.schema.json) and save it. The panel then shows the schema name `livewell_answer` under **Text format**. The pencil icon next to the name reopens the editor.
   4. Close the panel and select **Save** at the top right of the page to save a new version.

   The schema only accepts real guide ids in `cited_sources`, so the agent cannot invent a source. Do not pick **JSON Object**: that mode needs the word "json" in every chat message and otherwise fails with a 400 error.

   ![Parameters panel opened from the icon next to the Model dropdown, with Text format set to JSON Schema](screenshots/lab-01/06-json-response-format.png)
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

<details>
<summary><b>Explore further: how Foundry IQ works</b> (optional, about 10 min of reading)</summary>

**Why you attach one instead of building one.** A knowledge base built from files needs a knowledge source, and each source creates its own search index plus an indexer that chunks and embeds every file. The workshop's search service is on the Basic tier, which allows up to 15 indexes, 15 knowledge sources and 15 knowledge bases per service (5 on older services). A room of more than 15 people can't each have one, and each build adds embedding cost and ingestion time before the first question. One shared knowledge base keeps the cost fixed and lets Lab 1 start in seconds. Your own projects follow the same pattern: build one knowledge base per knowledge domain and reuse it across agents.

**What a knowledge base is.** It is the entry point for one knowledge domain. It holds the retrieval policy (how hard to search, what to steer towards, what to return) and points at one or more knowledge sources. Your agent reaches it through the knowledge base's MCP endpoint, which is why traces show a `knowledge_base_retrieve` tool call. Apps can also call the Retrieve API or SDK directly; `scripts/build-kb.py` does that for its retrieval check.

**How a question flows (agentic retrieval).**

```mermaid
flowchart TB
    agent["Your coach agent"]
    subgraph kb["Knowledge base: livewell-guides-kb"]
        direction LR
        plan["1 · Plan<br/>LLM turns the question<br/>into subqueries"] --> search["2 · Search in parallel<br/>keyword + vector (hybrid)"]
        search --> rank["3 · Rank and merge<br/>semantic reranker"]
        rank -.->|"medium effort only:<br/>one more pass if results are weak"| plan
    end
    ks[("Knowledge source livewell-guides-ks<br/>one index of 11 guide PDFs")]
    agent <-->|"MCP tool call knowledge_base_retrieve<br/>returns extractive passages + references"| kb
    kb <-->|"subqueries / matching chunks"| ks
```

**Knowledge sources: indexed or remote.** A knowledge base can mix both, and all results go through the same ranking.

| Kind | How it works | Examples |
|---|---|---|
| Indexed | Content is chunked, embedded and copied into a search index ahead of time, then searched with keyword, vector or hybrid queries. Replies can carry citation links. | Azure Blob (used here), OneLake, Azure SQL, file upload, indexed SharePoint, an existing search index |
| Remote (federated) | Nothing is indexed. The source is queried in place at question time through its own API. | Remote SharePoint, Fabric data agent, Fabric ontology, MCP server, Work IQ, Web (Bing) |

**The settings, and what `livewell-guides-kb` uses.**

| Setting | What it controls | `livewell-guides-kb` | Why |
|---|---|---|---|
| **Retrieval reasoning effort** ⚠️ preview | How much LLM planning runs before searching (limits below) | Low | Eleven short guides need one planning pass, and replies stay quick |
| **Output mode** ⚠️ preview | **Extractive data** returns the matching passages and your agent writes the answer. **Answer synthesis** has the knowledge base write a cited answer itself. | Extractive data | Your agent must answer in its own voice and JSON schema, so it needs passages, not a finished answer |
| **Retrieval instructions** ⚠️ preview | Plain-language hints for query planning and source selection | Lists the guide topics and says medication, supplements and diagnosis are not covered | Steers the planner away from loosely related guides on questions like `lab1_supplement` |
| **Chat completions model** | The model that plans the subqueries (and writes the answer in synthesis mode) | `gpt-5-mini` | A small, fast model is enough for planning |
| **Knowledge sources** | Where to search | `livewell-guides-ks`: Azure Blob, 11 guide PDFs | One domain, one source |

This is the settings page of the shared knowledge base. It lives under **Knowledge** in the left nav, not on the agent. If you open it, look but don't select **Save**: a change there affects every participant. Starting a new knowledge base shows the same fields on a blank form; cancel before you create it.

![Settings page of livewell-guides-kb: chat completions model, retrieval reasoning effort Low, output mode Extractive data, retrieval instructions and one knowledge source](screenshots/lab-01/04-kb-settings-preview.png)

**Retrieval reasoning effort trades cost and latency for depth.**

| Effort | Query planning | Max sources selected | Max queries per source | Max output tokens | Retrieval iterations |
|---|---|---|---|---|---|
| Minimal | None: every source is searched directly | 10 (all searched) | 10 | 10k | n/a |
| **Low** (default, used here) | One LLM planning pass | 3 | 3 | 10k | 1 |
| Medium | Planning, then a relevance check that allows one retry with a revised plan | 5 | 5 | 20k | 2 |

Minimal is the cheapest and fastest but needs Extractive data output and can't use answer synthesis or web sources. Medium gives the most complete results and is available in selected regions only. Newer API versions add **Auto** (preview), which starts light and goes up to medium only when the first pass isn't enough.

**Learn more:** [What is Foundry IQ?](https://learn.microsoft.com/azure/foundry/agents/concepts/what-is-foundry-iq) · [Agentic retrieval overview](https://learn.microsoft.com/azure/search/agentic-retrieval-overview) · [Knowledge sources](https://learn.microsoft.com/azure/search/agentic-knowledge-source-overview) · [Set the retrieval reasoning effort](https://learn.microsoft.com/azure/search/agentic-retrieval-how-to-set-retrieval-reasoning-effort) · [Answer synthesis](https://learn.microsoft.com/azure/search/agentic-retrieval-how-to-answer-synthesis) · [Agentic retrieval limits](https://learn.microsoft.com/azure/search/search-limits-quotas-capacity#agentic-retrieval-limits)

</details>

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

1. **The knowledge tool.** [`lw.kb_tool()`](../assets/common/livewell_common.py#L471-L475) returns an `MCPTool` that points at the knowledge base's MCP endpoint. It goes through the project connection `livewell-guides-kb-mcp`, so the project's managed identity signs in and the file holds no URL or key. `allowed_tools=["knowledge_base_retrieve"]` exposes only the search tool.
2. **The agent.** [`lw.create_agent(...)`](../assets/common/livewell_common.py#L644-L666) calls `project().agents.create_version(...)` with a `PromptAgentDefinition`: the model, the instructions, the tools, a strict JSON-schema response format and the guardrail. Each run adds a version to the same agent, as **Save** does in the portal.

   ```python
   coach = lw.create_agent("coach", instructions, tools=[knowledge],
                           schema=lw.lab1_schema(), rai_policy=lw.DEFAULT_RAI_POLICY)
   ```

3. **The question.** [`lw.ask(coach, prompt_id=...)`](../assets/common/livewell_common.py#L890-L970) sends the prompt through the OpenAI Responses API with `extra_body={"agent_reference": {"name": ..., "version": ...}}`. Foundry runs the agent on the server: it calls the knowledge base, then the model, then returns the JSON reply. The helper records the tools called, the routed model and the citations, and [`lw.expect`](../assets/lab1_knowledge.py#L75-L79) prints the PASS lines.

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

`lab1_supplement`: "The LiveWell guides don't cover this", `route` `clinician` and an empty `cited_sources`. `intent` may be `out_of_scope` or `nutrition`; either is fine, because the route is what sends him to a clinician. The agent still searched the guides, found nothing about supplements and said so.

![route clinician and empty cited_sources for the supplement prompt](screenshots/lab-01/11-json-route-clinician.png)

**Builder.** The same two answers, each followed by its PASS lines, then the CHECKPOINT block. Look for `tools: knowledge_base_retrieve` on both runs, five PASS lines for the food answer and three for the supplement answer. The `model:` field shows the model that answered (`gpt-5-mini`).

![lab1_knowledge.py output: coach created, cited food answer with five PASS lines, clinician route with three PASS lines, then the CHECKPOINT JSON](screenshots/lab-01/builder-output.png)

</details>

## Troubleshooting

| Symptom | Fix |
|---|---|
| **Connect to Foundry IQ** is not visible | You may be in Tools instead of Knowledge, or the portal preview has shifted. Ask the facilitator and use the portal-track fallback if shown. |
| **`livewell-guides-kb`** is not listed | Refresh, confirm you are in `livewell-workshop`, then ask the facilitator to check the shared knowledge base and your Foundry User access. |
| No settings page after attaching `livewell-guides-kb` | Expected: attaching a shared knowledge base doesn't open its settings. See **Explore further** at the end of the Navigator steps. |
| Can't find **Response format** | It is called **Text format**, inside the **Parameters** panel. Open it with the sliders icon to the right of the **Model** dropdown. |
| Agent returns prose instead of JSON | In **Parameters** → **Text format**, choose **JSON Schema**, paste [`lab1-answer.schema.json`](../config/schemas/lab1-answer.schema.json), save a new version, and re-run the prompt in a new chat. |
| Cited source is empty for `lab1_prediabetes_eat` | Re-check that `livewell-guides-kb` is attached and that the [`knowledge`](../prompts/coach-instructions.md#knowledge-lab-1) block is appended. |
| It invents a supplement source | Tighten the knowledge block by re-copying it, then send `lab1_supplement` again in a new conversation. |
| Builder script sees 5xx from the service | Re-run with `--verbose`; the script retries transient 5xx automatically. |
| 429 or quota errors | Wait 30 seconds and resend. If it keeps happening, switch the agent model to `gpt-4.1-mini` and tell the facilitator. |
| The answer cites web pages, or the trace shows a `web_search` call | The **Build an agent** template attached **Web search** in Lab 0. Remove it under **Tools**, save a new version, and re-run the prompt in a new chat. |
| The trace shows no `knowledge_base_retrieve` call | Check **Parameters → Reasoning effort**: keep it on **Low**. **Minimal** often answers without searching the guides. |
| 400 "must contain the word 'json'" | **Text format** is set to **JSON Object**. In **Parameters**, switch it to **JSON Schema** and paste [`lab1-answer.schema.json`](../config/schemas/lab1-answer.schema.json). |

## Where next

Go to [Lab 2 · Guardrails, Evaluations & Tracing](lab-02.md) to prove the grounded coach is safe and auditable. Keep [README](../../README.md) open for timing and checkpoint gates.
