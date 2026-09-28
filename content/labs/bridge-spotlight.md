# Bridge spotlight · Two IQs, one agent

**10 min** · **Facilitator spotlight** · **Level:** L200 · **Rails:** slides + optional demo · **Patterns:** revisit #1-#10 across the day

**You are here:** [Lab 0](lab-00.md) → [Lab 1](lab-01.md) → [Lab 2](lab-02.md) → [Lab 3](lab-03.md) ([Fabric step](fabric-step.md)) → [Lab 4](lab-04.md) → **Bridge spotlight** · [README](../../README.md)

## Shared objective

> Know when to reach for Foundry IQ (documents and knowledge) versus Fabric IQ (governed business data and ontology), and how to connect them

Patterns: revisit #1-#10; this spotlight adds no new build checkpoint.

## Foundry features covered

- Foundry IQ for documents, guides and cited knowledge answers.
- Fabric IQ tool ⚠️ preview for governed business data via a published Fabric data agent.
- OneLake or Fabric IQ as a Foundry IQ knowledge source ⚠️ preview.
- Ontology MCP server ⚠️ preview as a direct semantic-data path.
- Function or OpenAPI tool over a Fabric ML `/score` endpoint, if one exists.
- Guardrails, evaluations and hosted deployment as the cross-cutting governance layer.

## Story chapter

[Chapter 5](../narrative/rahim.md#chapter-5--two-iqs-one-agent-bridge-spotlight) closes the arc by bringing Mei's multi-hop Fabric question back to the same coach. The named ontology edges keep home region and event region separate, while the coach stays aggregate-only. Rahim's story never needed Fabric; Mei's programme questions did.

## 🟢 Navigator

This is a facilitator-led spotlight. Slides-only when the Lab 3 Fabric step is live; full demo when the Fabric step is skipped.

1. Start with their Fabric medallion estate:
   - `resident_360`.
   - Semantic model.
   - `resident_ontology`.
   - Fabric data agents.
   - Optional ML endpoint.
2. Bridge it to Foundry:
   - Foundry IQ for LiveWell guides and citations.
   - Fabric IQ tool for programme questions.
   - Profile + activities tools for personalisation and action.
   - Memory for preferences.
   - Guardrails and evaluations for governance.
   - Hosted deploy for system integration.
3. Use this decision table:

   | Use | Foundry IQ | Fabric IQ |
   |---|---|---|
   | Best for | Documents, guides, policies, FAQs, unstructured knowledge | Governed business data, semantic models, ontology-backed aggregates |
   | Example | Rahim asks what to eat and needs guide citations | Mei asks which regions or programmes need attention |
   | Output | Cited answer from knowledge sources | Aggregate answer from Fabric under user permissions |
   | Avoid | Programme analytics and row-level business questions | Citizen self-care questions and individual profile lookups |

4. Explain the three Fabric integration paths:

   | Path | Prerequisite | Status |
   |---|---|---|
   | Fabric IQ tool | Published Fabric data agent in OneLake Catalog, exposed through MCP | ⚠️ preview |
   | OneLake or Fabric IQ as a Foundry IQ knowledge source | Indexed files or supported source connected to the knowledge base | ⚠️ preview |
   | Ontology MCP server | Ontology endpoint and delegated permissions | ⚠️ preview |

   Optional fourth path: function or OpenAPI tool over a Fabric ML `/score` endpoint when a scoring service exists.
5. Send Mei's multi-hop question (`bridge_q_dropped_attended_heldin`) if doing the live demo:

   ```text
   Among residents who dropped a programme, how many attended at least one event, broken down by the region where those events were held?
   ```

   The ontology traversal is `enrolledIn` → `attended` → `heldIn`, keeping home region and event region apart.
6. Mention the optional Forgebook notebook by name: `Microsoft IQ in Foundry` on `microsoft-foundry.github.io/forgebook`.
7. Close on the extended arc: **Unify → Govern → Personalise → Converse → Coach & Act**.

Facilitator close-out prompts:

- Which part of today's agent used curated documents?
- Which part used governed business data?
- Which part required human approval before action?
- Which trace would you show an auditor first?

## 🔵 Builder

```bash
INITIALS=demo python content/assets/lab3_tools.py --fabric --verbose
```

```powershell
$env:INITIALS = "demo"
python content\assets\lab3_tools.py --fabric --verbose
```

This is optional facilitator replay, not a participant build. If the Fabric step already ran live, keep this section as slides-only.

What the replay does per cell:

1. Confirms the Fabric IQ tool connection used in [Fabric step](fabric-step.md).
2. Sends the bridge question and records the Fabric IQ trace.
3. Shows that the same coach still routes Rahim's citizen prompt to the knowledge base.
4. Prints the decision-table summary for discussion.

Use `--cleanup` only if you created demo agents named `livewell-demo-*` outside the protected facilitator set; participant cleanup remains guarded to `livewell-<INITIALS>-*`.

## Checkpoint

✅ **Built** shared understanding of the two IQ patterns.

✅ **Did** a decision-table walk-through, with a live or slide-based Fabric bridge.

✅ **Learned** how to choose the right grounding path before adding tools to an agent.

Paste into the checkpoint form: one sentence saying when you would use Foundry IQ, one sentence saying when you would use Fabric IQ, and the Fabric traversal for `bridge_q_dropped_attended_heldin`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Audience asks why not put everything in Foundry IQ | Use the decision table: documents belong in Foundry IQ; governed aggregate business data belongs in Fabric IQ. |
| Fabric demo is unavailable | Run slides-only and point back to [Fabric question bank](../fabric/question-bank.md). |
| Multi-hop answer confuses home region and event region | Emphasise the `heldIn` edge and the distinction documented in [data-agent instructions](../fabric/data-agent-instructions.md). |
| Demo includes individual detail | Stop the demo and show the aggregate-only privacy rule in [data-agent instructions](../fabric/data-agent-instructions.md). |
| OneLake Catalog item is missing | It is either unpublished or the account is in the wrong tenant. Use the facilitator screenshot or pre-recorded trace. |
| Participants ask for endpoint values | Values stay on the facilitator values sheet and in environment files, never in lab pages. |

## Where next

Return to [README](../../README.md) for the full workshop map, or revisit [Lab 4](lab-04.md) to see how the bridge is protected when the agent is hosted.
