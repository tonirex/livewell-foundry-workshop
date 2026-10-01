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
- Multi-step tool chaining in one turn: profile tool → Fabric IQ → activities MCP → approval-gated action.
- Privacy by design: the coach asks Fabric an aggregate cohort question (age band only), never about a person.
- Tool routing instructions that separate citizen guide questions, Rahim's one cohort question and officer programme questions.
- Trace validation: what the coach sent to Fabric, Fabric IQ for Mei's question, and no Fabric call for Rahim's food question.
- Fabric ontology and data agent ⚠️ preview over the Resident 360 estate, including the `droppedOut` edge.

## Story chapter

[Chapter 3](../narrative/rahim.md#chapter-3--its-hazy-today--what-can-i-do-indoors-lab-3--tools-mcp--memory) ends with two Fabric beats. In ch3.6 Rahim admits he dropped out of <!--ref:q_programme_fit.dropped_programme-->Healthier SG<!--/ref--> and asks which programme people his age actually stick with. The guides know *what* helps with pre-diabetes; only the governed Resident 360 knows *who stays*. In ch3.7 Mei asks a region-level planning question. The coach calls Fabric for both, but for Rahim it asks about his age band, never about him, and it still answers his food questions from Foundry IQ.

### Why Fabric makes this answer better

Without Fabric the coach can only say "any of these programmes could help". With Fabric it can reason over four sources in one turn:

| Step | Source | What the coach learns |
|---|---|---|
| 1 | `livewell_profile` (his own record) | Age band <!--ref:q_programme_fit.age_band-->60-64<!--/ref-->, pre-diabetes, High screening risk, Woodlands, the programmes he is in or dropped |
| 2 | Fabric IQ (Resident 360 ontology) | For the <!--ref:q_programme_fit.cohort_residents-->97<!--/ref--> residents in his age band: how many joined each programme and how many dropped out |
| 3 | Its own reasoning | <!--ref:q_programme_fit.dropped_programme-->Healthier SG<!--/ref--> lost <!--ref:q_programme_fit.dropped_programme_dropout_pct-->37.1<!--/ref-->% of them; <!--ref:q_programme_fit.recommended_programme-->Diabetes Prevention<!--/ref--> lost <!--ref:q_programme_fit.recommended_dropout_pct-->21.6<!--/ref-->%, the lowest of the programmes he is not already in, and it targets his glucose |
| 4 | Activities MCP | The <!--ref:q_programme_fit.recommended_programme-->Diabetes Prevention<!--/ref--> intake session near Woodlands, then `register_interest` after he approves |

```mermaid
sequenceDiagram
    actor R as Rahim
    participant C as LiveWell Coach
    participant P as livewell_profile
    participant F as Fabric IQ (Resident360 Ontology Agent)
    participant A as Activities MCP
    R->>C: Which programme do people my age stick with? Sign me up near Woodlands
    C->>P: get_citizen_profile(me)
    P-->>C: age band, pre-diabetes, Woodlands, his programmes
    C->>F: For residents in age band 60-64, how many enrolled in each programme and how many dropped out?
    F-->>C: enrolled and dropped per programme (aggregates only)
    Note over C: lowest drop-out he is not in, and fits pre-diabetes
    C->>A: find_activities(area Woodlands, pre-diabetes)
    A-->>C: Diabetes Prevention intake session
    C-->>R: recommendation, cohort numbers, shall I register you?
    R->>C: Yes
    C->>A: register_interest (waits for approval)
```

Privacy is part of the design. The question sent to Fabric names only the age band: no name, resident_id, planning area or gender. Adding his screening risk would shrink the cohort to about twenty people and every drop-out count would fall under the "fewer than 5" rule, so the cohort stays at age band only. Any count under five is reported as "fewer than 5".

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
2. Go to **Tools** → **Add** → **Add tools** → **Configured** → **Fabric IQ (OneLake Catalog)** ⚠️ preview → **Add tool**, and filter the catalog by `Resident360`.
3. Pick **`Resident360 Ontology Agent`** → **Add**, or, if the facilitator pre-created it, select the existing connection **`livewell-fabric-resident360`** on the **Configured** tab → **Add tool**.
4. In **Instructions**, append the `fabric` block from [coach-instructions.md](../prompts/coach-instructions.md). Link to the file; do not copy from this lab page.
5. Start a new conversation as Rahim. Send (`lab3_programme_fit`):

   ```text
   I dropped out of Healthier SG last year. Which programme do people my age actually stick with? Find me a way to start near Woodlands and sign me up.
   ```

   Expect, in order: the profile call, one Fabric IQ call (**30-90 s**), `find_activities`, then an approval card for
   `register_interest`. The reply should recommend **<!--ref:q_programme_fit.recommended_programme-->Diabetes Prevention<!--/ref-->**
   (<!--ref:q_programme_fit.recommended_dropout_pct-->21.6<!--/ref-->% drop-out in his age band against
   <!--ref:q_programme_fit.dropped_programme_dropout_pct-->37.1<!--/ref-->% for <!--ref:q_programme_fit.dropped_programme-->Healthier SG<!--/ref-->) and offer
   its intake session in Woodlands.

   Open the trace and select the Fabric IQ call. Its `userQuestion` argument is what left the coach. It should name
   the age band and nothing else. Approve the card to finish the sign-up.
6. Start a new conversation as Mei, the programme officer. Send (`fabric_q_disengaged_regions`):

   ```text
   Which regions have the highest share of disengaged residents?
   ```

   Expect the trace to show a Fabric IQ MCP call. Latency of **30-90 s** is normal for the preview path.
   The reference answer ranks **<!--ref:q_disengaged_regions.top_region-->North<!--/ref-->** first (<!--ref:q_disengaged_regions.top_share_pct-->20.0<!--/ref-->% of
   its residents are disengaged), then <!--ref:q_disengaged_regions.second_region-->West<!--/ref--> (<!--ref:q_disengaged_regions.second_share_pct-->17.1<!--/ref-->%).
7. Start a new conversation as Rahim. Send (`lab1_prediabetes_eat`):

   ```text
   My screening says my glucose is high. What should I eat to manage pre-diabetes?
   ```

   Confirm the trace shows knowledge-base retrieval and **no Fabric call**.

Routing rule to keep in mind:

| Seat | Question type | Expected tool |
|---|---|---|
| Rahim | Food, activity, sleep, screening, personal self-care | Foundry IQ knowledge base plus profile tool |
| Rahim | Which programme people like him stick with | Profile tool, then Fabric IQ with his age band only, then activities MCP |
| Rahim | Individual profile | Profile tool only, never Fabric |
| Mei | Region, programme, event, challenge aggregates | Fabric IQ tool |
| Anyone | Another resident's data | Refuse |

The checkpoint is about routing as much as the answer. A correct region table with the wrong tool path is not a pass, and a good programme recommendation that sent Rahim's name or area to Fabric is not a pass either.

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
6. Runs `lab3_programme_fit`, approves `register_interest`, and checks that the profile was read before the Fabric
   call, that the question sent to Fabric names the age band and no personal detail, and that the reply recommends
   the reference programme. The sent question is saved in `.runs/lab3-<INITIALS>.json`.

Use `--verbose` to print tool-call timing. Use `--cleanup` to delete only `livewell-<INITIALS>-*` agents. Optional extension: if a Fabric ML `/score` endpoint exists, the facilitator may expose it as a function tool, but it is not required for the checkpoint.

When `FABRIC_BRIDGE=false`, run Lab 3 without `--fabric`; the profile tool still personalises from [citizens.json](../data/citizens.json).

Keep Fabric disabled in local experiments unless the facilitator confirms the shared connection is ready.

## Checkpoint

✅ **Built** a coach that chains profile, Fabric IQ and activities tools to make one personal decision, and routes officer aggregate questions to Fabric IQ while keeping citizen guidance in Foundry IQ.

✅ **Did** a programme-fit run with an approval, one Fabric IQ trace check for Mei and one no-Fabric citizen check.

✅ **Learned** that Fabric IQ adds governed population evidence to a personal answer, as long as the question sent to it stays aggregate.

Paste into the checkpoint form: the `userQuestion` the coach sent to Fabric for `lab3_programme_fit` and the programme it recommended (**<!--ref:q_programme_fit.recommended_programme-->Diabetes Prevention<!--/ref-->**), the trace line showing the Fabric IQ MCP call for `fabric_q_disengaged_regions`, the grouped-by-region answer, and confirmation that `lab1_prediabetes_eat` produced no Fabric call. The top region should be **<!--ref:q_disengaged_regions.top_region-->North<!--/ref-->** (±1 rank, from `content/fabric/reference-answers.json`), and the answer must not include any `resident_id`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Data agent is not in OneLake Catalog | It may not be published, or you may be signed into a different tenant/account. Use the same lab account in Foundry and Fabric. |
| 403 from Fabric | Ask the facilitator to confirm read access on **`Resident360 Ontology Agent`** for your lab account. |
| Graph query failing | Facilitator refreshes the graph model `resident_ontology_graph_*` from Fabric: Schedule → Refresh now. |
| Fabric call is slow | Normal preview latency is **30-90 s**; wait before retrying. |
| Citizen food question calls Fabric | Re-copy the `fabric` routing block and verify the knowledge base remains attached. |
| Programme-fit question sent Rahim's area, name or risk to Fabric | Re-copy the `fabric` block; it fixes the question to the age band only. Run the prompt again in a new chat. |
| Coach recommends a programme Rahim is already in, or <!--ref:q_programme_fit.dropped_programme-->Healthier SG<!--/ref--> again | Check the profile call ran first; the `programmes` field lists his active and dropped programmes. |
| No intake session found | The activities MCP server needs the latest `activities.json` (the intake session has a `programme` field). The facilitator runs `azd deploy mcp-activities`. |
| Fabric shows a count under 5 as a number | Ask the facilitator to re-apply the [data-agent instructions](../fabric/data-agent-instructions.md) small-cell rule. |
| Fabric answer includes individual detail | Stop and re-run after the facilitator checks [data-agent instructions](../fabric/data-agent-instructions.md); Fabric answers must be aggregate-only. |
| `FABRIC_BRIDGE=false` | Skip this page. Lab 3 profile still works from [citizens.json](../data/citizens.json). |

## Where next

Return to [Lab 3](lab-03.md) if you have not completed the activity and memory checkpoints, then continue to [Lab 4](lab-04.md). Keep [README](../../README.md) open for the optional path guidance.
