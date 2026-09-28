# Changelog

All notable changes to this workshop. One entry per phase PR.

## [Unreleased]

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
