# Fabric question bank — Mei Lin's questions

Mei Lin (fictional HPB programme officer) is the **only** reason LiveWell Coach calls Fabric. She asks
exactly **three** questions, each tied to one lab checkpoint. Every `fabric` beat in
`content/narrative/rahim.md` points at one of these ids, and every id has a prompt in
`content/prompts/test-prompts.json`. Reference answers are recomputed from the data by
`scripts/validate-narrative.py` into `reference-answers.json` — never copy numbers from a portal run.

| question_id | Question (verbatim) | prompt_id | Where it is used | Traversal | Live gate |
|---|---|---|---|---|---|
| `q_disengaged_regions` | Which regions have the highest share of disengaged residents? | `fabric_q_disengaged_regions` | [Lab 3 Fabric step](../labs/fabric-step.md) checkpoint | Resident —livesIn→ Region (filter `is_disengaged = 1`) | **strict** — exact counts, top region ±1 rank |
| `q_dropped_attended_heldin` | Among residents who dropped a programme, how many attended at least one event, broken down by the region where those events were held? | `bridge_q_dropped_attended_heldin` | [Bridge spotlight](../labs/bridge-spotlight.md) | Resident (`programmes_dropped ≥ 1`) —attended→ EventOccurrence —heldIn→ Region | **advisory** — multi-hop over a preview ontology (kit Lab 4 lesson) |
| `q_programmes_disengaged_enrolled` | Which programmes have the most disengaged residents enrolled? | `lab4_q_programmes_disengaged` | [Lab 4](../labs/lab-04.md) Programme-Insights specialist | Resident (`is_disengaged = 1`) —enrolledIn→ Programme | **strict** — exact counts, top programme ±1 rank |

**Why would Mei ask Fabric here, and what does the coach do with the answer?** (the table-read test)

1. `q_disengaged_regions` — Mei is deciding where to run the next re-engagement roadshow. Only the
   governed Resident 360 knows who is disengaged; the coach returns the ranked regions and suggests
   pairing the top region with indoor, hazy-day-friendly activities from the activities catalogue.
2. `q_dropped_attended_heldin` — Mei wants to know whether people who drop programmes still turn up to
   events, and where. It needs the ontology's named `heldIn` edge (event region ≠ home region); the coach
   uses the answer to recommend running programme "come-back" booths at the busiest event regions.
3. `q_programmes_disengaged_enrolled` — Mei is reviewing which programme teams to brief first. The
   Programme-Insights specialist answers from Fabric; the coach turns it into a one-line brief per programme.

## Exploration questions (not in the narrative; for facilitators and curious participants)

Aggregate-only, adapted from the Resident 360 kit question bank (MIT, see NOTICE.md). They are not gated.

- How many residents are disengaged by age band?
- Compare average daily steps for residents who attended at least one event vs those who attended none.
- How many residents attended events in each region where the events were held?
- Which hazy regions have the lowest average MVPA?
- Healthpoints earned by home region, highest first.

## Never ask the data agent

- Anything that names a resident or a `resident_id` (the coach's `fabric` block forbids it; the data agent
  also refuses).
- Citizen questions ("what should I eat?") — those go to the Foundry IQ knowledge base.
