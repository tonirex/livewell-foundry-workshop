# Changelog

All notable changes to this workshop. One entry per phase PR.

## [Unreleased]

### Phase 5: Proof & demo kit (`phase-5-proof`)

- `scripts/smoke-test.py` (SPEC §11.2): temporary `livewell-smoke-*` agents built from the demo-agent definitions
  check the MCP server, knowledge base citation, guardrail, ≥ 2 tools, Fabric for Mei and not for Rahim, and the
  hosted agent, then print the cost since provision. `--demo-agents` tests the facilitator agents at T-0. It exits 1
  on a failure or a leftover agent. Verified 7/7 in `mcaps`.
- `demos/create-demo-agents.py`: the five portal-track reference agents `livewell-demo-{lab0,kb,guarded,tools,fabric}`
  from the same instruction blocks, schemas, tools and guardrail as the lab pages. All tools run server-side (the
  profile tool is an OpenAPI tool), so they work in the playground. Re-runs are idempotent (definition hash in the
  version metadata). It also registers the `livewell-eval` dataset that the Lab 2 portal evaluation picks.
  `livewell_common.profile_openapi_tool()` is shared with the smoke test.
- `demos/portal.py`, `demos/scenes.py`, `demos/capture-screenshots.py`, `demos/record-demos.py`: Playwright (Edge)
  kit for the new Foundry portal. It covers a one-time sign-in with a kept profile, 11 scenes that fill the Navigator
  screenshot slots, `--list-missing` and `--link`, and one captioned WebM per lab. Scenes never save; IDs, endpoints
  and e-mails are rewritten and the account button is masked. `requirements-demos.txt` (Playwright ≥ 1.47).
- `content/labs/screenshots/`: Navigator screenshots for Labs 0–4, linked into the portal lab pages. Five slots stay
  manual (two lab-account sign-in shots, two Foundry User views of the hosted agent, and the v1/v2 evaluation
  comparison).
- `demos/DRY-RUN-TEMPLATE.md`: dry-run report (gates, timed run of show per rail, open questions from
  ASSUMPTIONS, findings with severity, cost and cleanup, sign-off) that Phase 6 works from.
- The values sheet refreshes by itself: the `postprovision` hook (after the guardrail), a new project `postdeploy`
  hook, `scripts/fabric/deploy.sh` and `scripts/connect-tools.py` all run `render-values.py`. The sheet adds the
  profile OpenAPI URL (Lab 3) and the hosted agent name (Lab 4).
- Lab 1 portal: step 3 names the Connect to Foundry IQ dialog fields, and step 4 opens the knowledge base page
  directly (it opens on its settings).
- Lab 2 portal: the injected flyer is pasted below the prompt instead of attached. The playground accepts only
  image and PDF attachments, and a rejected `.md` file blocks Send. Step 13 opens the blocked run from the agent's
  Traces tab (a guardrail-blocked chat turn has no metrics row or Traces button). Step 15 follows the live
  evaluation wizard: row Version picker, `livewell-eval` dataset, Context set to Not available, and seven evaluators
  instead of the 22 suggested.
- Lab 3: the profile tool is `livewell_profile` (the portal rejects dashes in OpenAPI tool names) in the lab pages,
  answer keys, `connect-tools.py` and the demo agents. The portal OpenAPI step pastes the schema from the values
  sheet (Tools → Add → Add tools → Custom → OpenAPI tool). The MCP server and the Fabric IQ tool are added from the
  **Configured** tab of Select a tool (project connections), and the MCP approval rule is edited from the tool
  row's Actions → Configure. The Fabric step picks the Resident360 ontology agent in the OneLake Catalog. The
  register-interest prompt adds a "yes" follow-up because the coach asks before it signs Mei up. The approval step
  now reads **Approve → Approve once**, because Approve has become a split button.
- `scripts/check-content.py` skips the gitignored `demos/.playwright` (browser profile) and `demos/runs`.
- Docs: ADMIN-SETUP (demo-agent step at T-3, screenshot and video capture at T-1, smoke test at T-0, backups,
  script reference), run of show T-0 checklist, PORTAL-TRACK slot rules, versions.md (Playwright 1.63.0, portal
  surfaces), ASSUMPTIONS 5.x.

### Phase 4: Builder-rail code (`phase-4-labs`)

- `content/assets/common/livewell_common.py`: shared helper for every lab. It covers settings from `.env` and the
  azd env, `livewell-<INITIALS>-<role>` naming with protected prefixes, strict schemas with a guide-id enum, retries
  on transient errors, tools (KB, activities MCP with approvals, Fabric IQ, profile function, memory), `ask()` with
  function calls, approvals and guardrail blocks, hosted-agent routing, Lab 2 evaluation helpers, Agent Framework
  helpers, recorded checks, and `cleanup()`.
- Lab scripts in `# %%` cell form with `# 👉` retype lines, `--verbose` and `--cleanup`:
  `lab1_knowledge.py` (`--intake`), `lab2_govern.py` (`--eval-all`, `--no-eval`, `--upload`), `lab3_tools.py`
  (`--fabric`, `--no-memory`) and `lab4_multiagent.py` (`--fabric`, `--no-handoff`; sequential and handoff Agent
  Framework teams, Fabric insights agent, hosted-agent smoke test).
- Guardrail: `content/config/guardrails.yaml` drives the Bicep blocklist, the policy and the deployment
  attachments; `scripts/apply-guardrail.py` (postprovision) syncs the blocklist items and repairs drift (`--check`).
- `scripts/build-kb.py`: Foundry IQ knowledge base `livewell-guides-kb` (Blob or OneLake source) plus its MCP
  connection and a retrieval check.
- `content/assets/mcp-activities/`: FastMCP activities server (`find_activities`, `register_interest`) plus the
  session-scoped profile REST/OpenAPI endpoint, deployed with `azd deploy mcp-activities`.
- `scripts/connect-tools.py`: activities MCP and Fabric IQ connections, with end-to-end checks.
- `content/assets/hosted-agent-example/`: Agent Framework hosted agent `livewell-workshop-hosted` (code deploy), and
  `scripts/hosted-postdeploy.py` (azd postdeploy hook). The hook grants the agent identity Foundry User and attaches
  `livewell-guardrails`; `--check` and `--verify` are available.
- `content/eval/livewell-eval.jsonl` (30 rows) and the custom evaluator `advice_matches_conditions.py`.
- `scripts/red-team.py` and `requirements-redteam.txt`: facilitator AI Red Teaming Agent scan (lite ≈ US$0.85,
  full ≈ US$8), with the cost printed before the scan starts.
- `scripts/validate-builder-rail.py`: runs Labs 1–4 as `INITIALS=test`, checks the SPEC signals and leftovers, and
  writes a report.
- `scripts/gen-schemas.py` and `content/config/schemas/`: paste-ready Navigator schemas plus the hosted agent's
  `livewell.json`.
- Makefile targets `notebooks`, `validate-rail` and `clean-agents`. `validate-narrative.py` now reads the
  coach-routing row from the Lab 3 run.
- Models: `gpt-5.4-mini` deployment (200K TPM) for the Lab 3 coach with memory. Chat TPM caps go from 100K to 400K.
  RBAC is added for memory (the project identity) and the hosted agent identity.
- Storage: MCAPS policy opt-out tag, a resource-instance rule for Search, and `storageNetworkDefaultAction`
  (`Allow` by default: Entra-only public access, so Lab 2 and the red team can publish evaluation runs; `Deny`
  admits only Search and trusted services).
- Prompts: the `nutrition` and `activity` specialist blocks now end every answer with the guide ids used (moved
  from the `handoff` block), so the Lab 4 sequential Coach can cite them; `livewell.json` regenerated.
- Docs: lab pages 1–4 (Builder sections, JSON schema instead of JSON object, troubleshooting), ADMIN-SETUP
  (T-3 steps 4–7, the T-1 rail validation and red team, cost and RBAC rows, script reference), versions.md,
  ASSUMPTIONS 4.1–4.23.

### Phase 3b: narrative gate (`phase-3b-narrative-gate`)

- `scripts/validate-narrative.py` with three layers (`--layers static,data,live` or `all`), `--fill`, `--check`,
  `--runs`, `--pause`, `--questions`. Static: beats, seats, sources, prompts, glossary spelling, no `resident_id`,
  numbers only through `{{ref:...}}`, filled values current. Data: rebuilds Resident 360 with `r360.py`, checks
  joins, glossary rules, Rahim across citizens.json, intake documents and story, and writes
  `content/fabric/reference-answers.json`. Live: a graph check (canonical GQL on the graph model), then three
  data-agent calls per fabric question with latency, judged against the reference; writes
  `demos/NARRATIVE-VALIDATION-<date>.md` with every raw answer.
- `--fill` wrote 22 reference values into `content/narrative/rahim.md`, `bridge-spotlight.md`, `fabric-step.md` and
  `lab-04.md` as `<!--ref:key-->value<!--/ref-->` markers; `check-content.py` accepts them.
- Ontology: gold aggregates `Region.disengaged_residents`, `Region.disengaged_share_pct` and
  `Programme.disengaged_enrolled` (built by `r360.py`), so the two strict questions read one row per group.
- Data agent: `40-data-agent.py` deploys and publishes **data source instructions** (graph schema, flag conditions,
  GQL shapes, the 200-row query limit) alongside the agent instructions. Example queries are not supported for
  ontology sources.
- `question-bank.md`: canonical GQL per question (traversal and aggregate), used by the graph check and the bridge
  spotlight.
- `content/assets/Makefile` (`make validate`, `validate-live`, `fill`) and the manual CI workflow
  `.github/workflows/validate-narrative.yml`.
- ADMIN-SETUP: the proof step, F2 throttling and 200-row troubleshooting rows, and the script reference.

### Phase 3: minimal Resident 360 on Fabric (`phase-3-fabric`)

- `scripts/fabric/deploy.sh [env] [--from NN] [--only NN] [--skip-upload]` runs six idempotent steps with
  per-step timings: `10-workspace.sh`, `20-lakehouse-load.sh`, `30-ontology.py`, `35-graph-refresh.py`,
  `40-data-agent.py` and `90-write-env.py`. The shared helpers live in `fabriclib.py` and `notebook.py`.
- `content/assets/load_resident360.ipynb` imports `scripts/r360.py` from OneLake and writes the six Delta tables.
  It exports summary and CSV files for the local checks.
- The ontology `resident_ontology` (4 entity types, 4 relationship types) is rendered from
  `content/fabric/ontology.blueprint.yaml`. The graph refresh runs through the job API, and a GQL check confirms
  the instance counts.
- The data agent `Resident360 Ontology Agent` is created, its entity types are selected, and it is published.
  `scripts/fabric/ask.py` queries it over MCP.
- `scripts/gen-citizens.py --from-onelake` rebuilds `citizens.json` from the lakehouse export.
- Instructions: counting rules. Tenant setting renamed ("Users can create Ontology (preview) items").
  `teardown.sh` clears the new `FABRIC_*` keys.
- Verified in the `mcaps` environment: the table counts, the graph instances and the data agent answer all match
  the local reference. A full run takes 17–20 minutes on F2. `35-graph-refresh.py` reuses the refresh that the
  ontology update starts instead of running a second one.

### Phase 2: infrastructure and admin scripts (`phase-2-infra`)

- Bicep (`infra/`): Foundry account and project (model-router, gpt-4.1-mini, text-embedding-3-large;
  100K TPM caps), Azure AI Search Basic, storage, ACR, Log Analytics and App Insights, Container Apps
  environment with the MCP placeholder app (min replicas 0), Fabric F2 capacity (opt-out with
  `FABRIC_BRIDGE=false`), US$300 budget with alerts at 50% and 100%, facilitator and project RBAC.
- Per-environment parameters (`infra/env/mcaps.bicepparam`, `sponsor.bicepparam`) selected by
  `scripts/select-params.py`; `SEARCH_LOCATION` override for regional Search capacity shortages.
- Admin scripts: `preflight.sh` (8 checks), `provision.sh` (preflight, what-if, `azd provision`),
  `cost-guardrails.sh`, `capacity.sh`, `teardown.sh`, `seed-attendees.sh`, `tenant/create-lab-users.sh`,
  `render-values.py`, plus the `lib/` helpers (`common.sh`, `azrest.py`, `wsconfig.py`).
- Admin docs: `content/admin/ADMIN-SETUP.md`, `TENANT-BOOTSTRAP.md`, troubleshooting table.
- Verified in the `mcaps` environment: provision, guardrails, teardown and provision from empty.

### Phase 1: content and data (`phase-1-content`)

- Workshop config (`content/config/workshop.yaml`) and glossary (`content/config/glossary.yaml`).
- Resident 360 data: 7 vendored kit files (pinned at `3ce11e4`), Rahim overlay, and generated
  `activity_daily`, `health_screening` and `air_quality_snapshot` (`scripts/gen-activity.py`).
- Local gold build and reference answers (`scripts/r360.py`); 12 synthetic citizens
  (`scripts/gen-citizens.py`); 46 activities; injected flyer; Rahim intake documents.
- 11 LiveWell guides (markdown and PDF) for Foundry IQ.
- Lab pages 0–4, Fabric step and bridge spotlight, both rails; Portal Track.
- Prompt bank (`content/prompts/test-prompts.json`), coach instruction blocks, answer keys.
- Fabric ontology blueprint, data-agent instructions and question bank (Mei's 3 questions).
- Rahim narrative (6 chapters) with beat tags.
- Deck builder and 16:9 deck.
- README, facilitator run of show, ASSUMPTIONS, versions, NOTICE, devcontainer, `scripts/check-content.py`.

### Bootstrap

- SPEC.md, CODING-AGENT-PROMPTS.md, AGENTS.md, LICENSE, .gitignore.
