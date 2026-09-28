# Fabric step · Add the Resident 360 data agent as a Fabric IQ tool

**15 min** · **Optional** · **When:** `FABRIC_BRIDGE=true` · **Level:** L300 · **Rails:** 🟢 Navigator + 🔵 Builder · **Patterns:** #2 Evidence-Based Decision Support · #3 Workflow Orchestration · #6 Human-in-the-Loop Review · #8 Institutional Memory · #9 Collaboration Between Specialists

**You are here:** [Lab 0](lab-00.md) → [Lab 1](lab-01.md) → [Lab 2](lab-02.md) → [Lab 3](lab-03.md) (**Fabric step**) → [Lab 4](lab-04.md) → [Bridge spotlight](bridge-spotlight.md) · [README](../../README.md)

## Shared objective

> An agent that acts: personalise on governed data, take real actions with a human in the loop, delegate to specialists, and route each kind of question to the right tool

Patterns: #2 Evidence-Based Decision Support; #3 Workflow Orchestration; #6 Human-in-the-Loop Review; #8 Institutional Memory; #9 Collaboration Between Specialists.

## Foundry features covered

- Fabric IQ tool ⚠️ preview, connected to a published Fabric data agent through OneLake Catalog and MCP.
- Project connection **`livewell-fabric-resident360`**.
- Identity passthrough: participants must use the same lab account in Foundry and Fabric.
- Tool routing instructions that separate citizen guide questions from officer programme questions.
- Trace validation: Fabric IQ MCP call for Mei's question and no Fabric call for Rahim's guide question.
- Fabric ontology and data agent ⚠️ preview over the Resident 360 estate.

## Story chapter

[Chapter 3](../narrative/rahim.md#chapter-3--its-hazy-today--what-can-i-do-indoors-lab-3--tools-mcp--memory) includes a separate officer beat for Mei. She asks a programme-level question that belongs in governed Resident 360 data, not the LiveWell guide knowledge base. The coach should call Fabric for Mei's aggregate question, then return to Foundry IQ for Rahim's citizen food question.

## 🟢 Navigator

Prerequisites the facilitator completed:

- Fabric workspace **`HPB Resident 360`** is deployed.
- Lakehouse **`lh_resident360`** is loaded.
- Ontology **`resident_ontology`** exists; see [ontology blueprint](../fabric/ontology.blueprint.yaml).
- Published data agent **`Resident360 Ontology Agent`** exists with instructions from [data-agent instructions](../fabric/data-agent-instructions.md).
- Project connection **`livewell-fabric-resident360`** exists.
- Participants are signed in with the same account in Foundry and Fabric.
- User identity passthrough is enabled, and published agents appear in the OneLake Catalog.

Steps:

1. Open your Lab 3 agent.
2. Go to **Tools** → **Add tool** → **Fabric IQ** → **OneLake Catalog** ⚠️ preview.
3. Pick **`Resident360 Ontology Agent`**, or select the existing connection **`livewell-fabric-resident360`** if the facilitator pre-created it.
4. In **Instructions**, append the `fabric` block from [coach-instructions.md](../prompts/coach-instructions.md). Link to the file; do not copy from this lab page.
5. Start a new conversation as Mei, the programme officer. Send (`fabric_q_disengaged_regions`):

   ```text
   Which regions have the highest share of disengaged residents?
   ```

   Expect the trace to show a Fabric IQ MCP call. Latency of **30-90 s** is normal for the preview path.
6. Start a new conversation as Rahim. Send (`lab1_prediabetes_eat`):

   ```text
   My screening says my glucose is high. What should I eat to manage pre-diabetes?
   ```

   Confirm the trace shows knowledge-base retrieval and **no Fabric call**.

Routing rule to keep in mind:

| Seat | Question type | Expected tool |
|---|---|---|
| Rahim | Food, activity, sleep, screening, personal self-care | Foundry IQ knowledge base plus profile tool |
| Rahim | Individual profile | Profile tool only, never Fabric |
| Mei | Region, programme, event, challenge aggregates | Fabric IQ tool |
| Anyone | Another resident's data | Refuse |

The checkpoint is about routing as much as the answer. A correct region table with the wrong tool path is not a pass.

## 🔵 Builder

```bash
INITIALS=abc python content/assets/lab3_tools.py --fabric
```

```powershell
$env:INITIALS = "abc"
python content\assets\lab3_tools.py --fabric
```

Or open `content/assets/lab3_tools.py` and run the Fabric cells after the main Lab 3 cells. Use this only when the facilitator confirms `FABRIC_BRIDGE=true`.

What the script does per cell:

1. Loads the Fabric-enabled tool configuration from the environment.
2. Attaches the project connection **`livewell-fabric-resident360`** to the coach.
3. Appends the `fabric` instruction block from [coach-instructions.md](../prompts/coach-instructions.md).
4. Runs `fabric_q_disengaged_regions` and records the Fabric IQ MCP trace line.
5. Runs `lab1_prediabetes_eat` in the same agent and asserts no Fabric tool call is used.

Use `--verbose` to print tool-call timing. Use `--cleanup` to delete only `livewell-<INITIALS>-*` agents. Optional extension: if a Fabric ML `/score` endpoint exists, the facilitator may expose it as a function tool, but it is not required for the checkpoint.

When `FABRIC_BRIDGE=false`, run Lab 3 without `--fabric`; the profile tool still personalises from [citizens.json](../data/citizens.json).

Keep Fabric disabled in local experiments unless the facilitator confirms the shared connection is ready.

## Checkpoint

✅ **Built** a coach that can route officer aggregate questions to Fabric IQ while keeping citizen guidance in Foundry IQ.

✅ **Did** one Fabric IQ trace check and one no-Fabric citizen check.

✅ **Learned** that Fabric IQ is for governed business data and ontology questions, not individual citizen self-care advice.

Paste into the checkpoint form: the trace line showing the Fabric IQ MCP call for `fabric_q_disengaged_regions`, the grouped-by-region answer, and confirmation that `lab1_prediabetes_eat` produced no Fabric call. The top region should match `content/fabric/reference-answers.json` generated in Phase 3b, and the answer must not include any `resident_id`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Data agent is not in OneLake Catalog | It may not be published, or you may be signed into a different tenant/account. Use the same lab account in Foundry and Fabric. |
| 403 from Fabric | Ask the facilitator to confirm read access on **`Resident360 Ontology Agent`** for your lab account. |
| Graph query failing | Facilitator refreshes the graph model `resident_ontology_graph_*` from Fabric: Schedule → Refresh now. |
| Fabric call is slow | Normal preview latency is **30-90 s**; wait before retrying. |
| Citizen food question calls Fabric | Re-copy the `fabric` routing block and verify the knowledge base remains attached. |
| Fabric answer includes individual detail | Stop and re-run after the facilitator checks [data-agent instructions](../fabric/data-agent-instructions.md); Fabric answers must be aggregate-only. |
| `FABRIC_BRIDGE=false` | Skip this page. Lab 3 profile still works from [citizens.json](../data/citizens.json). |

## Where next

Return to [Lab 3](lab-03.md) if you have not completed the activity and memory checkpoints, then continue to [Lab 4](lab-04.md). Keep [README](../../README.md) open for the optional path guidance.
