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
6. Prints the participant checkpoint payload.

Use `--verbose` to print tool and citation details. Use `--cleanup` only when you want to delete agents created by the script; it is guarded to names starting with `livewell-<INITIALS>-*`. Lines you are expected to retype during the lab are marked `# 👉`.

## Checkpoint

✅ **Built** a knowledge-grounded coach that answers in JSON.

✅ **Did** one cited food-guidance answer and one no-source clinician route.

✅ **Learned** that retrieval is useful only when the agent is required to cite real sources and admit when the corpus is silent.

Paste into the checkpoint form: the JSON reply for `lab1_prediabetes_eat`, plus the JSON reply for `lab1_supplement`. If you ran the optional intake step, paste that JSON too.

## Troubleshooting

| Symptom | Fix |
|---|---|
| **Connect to Foundry IQ** is not visible | You may be in Tools instead of Knowledge, or the portal preview has shifted. Ask the facilitator and use the portal-track fallback if shown. |
| **`livewell-guides-kb`** is not listed | Refresh, confirm you are in `livewell-workshop`, then ask the facilitator to check the shared knowledge base and your Foundry User access. |
| Agent returns prose instead of JSON | Set Response format to **JSON object**, save a new version, and re-run the prompt. |
| Cited source is empty for `lab1_prediabetes_eat` | Re-check that `livewell-guides-kb` is attached and that the [`knowledge`](../prompts/coach-instructions.md#knowledge-lab-1) block is appended. |
| It invents a supplement source | Tighten the knowledge block by re-copying it, then send `lab1_supplement` again in a new conversation. |
| Builder script sees 5xx from the service | Re-run with `--verbose`; the script retries transient 5xx automatically. |
| 429 or quota errors | Switch to `gpt-4.1-mini` or wait for the facilitator's quota reset guidance. |
| 400 "must contain the word 'json'" | The response format is **JSON object**. Switch to **JSON schema** and paste [`lab1-answer.schema.json`](../config/schemas/lab1-answer.schema.json). |

## Where next

Go to [Lab 2 · Guardrails, Evaluations & Tracing](lab-02.md) to prove the grounded coach is safe and auditable. Keep [README](../../README.md) open for timing and checkpoint gates.
