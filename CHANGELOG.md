# Changelog

All notable changes to this workshop. One entry per phase PR.

## [Unreleased]

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
