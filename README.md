# LiveWell Coach: Microsoft Foundry Workshop

### *A healthy-living coach for Singapore residents, built on Microsoft Foundry and extended with Fabric IQ*

A one-day, hands-on workshop for the Health Promotion Board. You build **LiveWell Coach**, an agent that
answers healthy-living questions from curated guides with citations, personalises on a synthetic
Resident 360 profile, signs residents up for activities with a human in the loop, and answers a
programme officer's population questions through the **Fabric data agent the cohort built in the Fabric
workshop**. Fabric built the Resident 360 that sees Rahim; today Foundry builds the coach that talks to him.

---

## 👉 Start here

**Everyone starts at Lab 0 and goes in order.** Pick a rail inside each lab; you can switch between labs.

| Lab | Title | What you build | Time |
|-----|-------|----------------|------|
| **▶ [Lab 0](content/labs/lab-00.md)** | Setup & first agent | `livewell-<initials>`: model + instructions, model-router compared with gpt-4.1-mini | 15 min |
| [Lab 1](content/labs/lab-01.md) | Agents & Knowledge: Foundry IQ | Foundry IQ knowledge base, citations, JSON contract | 40 min |
| [Lab 2](content/labs/lab-02.md) | Guardrails, Evaluations & Tracing | RAI policy, four red-flag prompts, traces, batch evaluation, v1 vs v2 | 40 min |
| [Lab 3](content/labs/lab-03.md) | Tools, MCP & Memory: hyper-personalisation | Profile tool, activities MCP with approval, memory, specialists | 40 min |
| [Fabric step](content/labs/fabric-step.md) | Add the Fabric IQ tool (optional, in Lab 3) | Mei's region question answered by the Resident360 Ontology Agent | 15 min |
| [Lab 4](content/labs/lab-04.md) | Multi-agent & Hosted deploy *(facilitator demo)* | Agent Framework orchestration, hosted agent with guardrails | 30 min |
| [Bridge spotlight](content/labs/bridge-spotlight.md) | Two IQs, one agent *(facilitator)* | How the Fabric medallion and Foundry fit together | 10 min |

**Pick your rail** (every lab has 🟢 Navigator and 🔵 Builder sections):

| Rail | For | You work in | Setup needed |
|------|-----|-------------|--------------|
| 🟢 **Navigator** | Programme officers, IT leaders, anyone who prefers the browser | The **Foundry portal** | A browser and your workshop sign-in |
| 🔵 **Builder** | Developers, data engineers, technical PMs | Python scripts in `content/assets/` (cell form, open as notebooks) | Codespaces *(recommended)* or local Python |

> 🟢 **Navigator: you're done reading. [Start Lab 0](content/labs/lab-00.md).** Prefer screenshots? Use the [Portal Track](content/labs/PORTAL-TRACK.md).

> 🔵 **Builder: skim [Builder setup](#-builder-setup) below, then start Lab 0.**

### The ten agentic patterns in LiveWell

| # | Pattern | Lab | What you see |
|---|---------|-----|--------------|
| 1 | Multi-Document Understanding | 1 | Rahim's screening summary + activity diary → structured JSON intake |
| 2 | Evidence-Based Decision Support | 3 | `{advice, confidence, supporting_guides[], rationale, personalisation_flags[]}` |
| 3 | Workflow Orchestration | 3 / 4 | Coach orchestrator → Nutrition + Activity specialists |
| 4 | Knowledge Retrieval | 1 | Foundry IQ knowledge base; citations mandatory |
| 5 | Explainability & Traceability | 2 | Citations, traces, evaluator scores, monitoring |
| 6 | Human-in-the-Loop Review | 3 | Approval card before `register_interest` |
| 7 | Handling Uncertainty | 2 | Route to a clinician or HealthHub; never dose medication; "insufficient information" |
| 8 | Institutional Memory | 3 | Memory of stated preferences ("I prefer mornings") |
| 9 | Collaboration Between Specialists | 3 / 4 | Nutrition + Activity + Programme-Insights specialists, one merged reply |
| 10 | Governance & Safety | 2 + throughout | Guardrails, evaluators, red-team scan, RBAC, Entra Agent ID |

---

## Before the day

<details>
<summary><strong>Logistics for participants</strong></summary>

- **Bring a personal laptop.** WOG devices cannot sign in to an external Entra tenant.
- **Guest Wi-Fi:** SSID and code are on the welcome slide (set in `content/config/workshop.yaml`).
- **First sign-in:** you get a workshop account (`hpb.labNN@…`) and a temporary password. At first
  sign-in you change the password and register **Microsoft Authenticator** on your phone. Install it before the day.
- Use a private or guest browser window so your work account does not interfere.

</details>

## 🔵 Builder setup

<details>
<summary><strong>Option A · GitHub Codespaces (recommended, ~3 min)</strong></summary>

The dev container gives everyone the same x64 Linux image: Python 3.13, uv, `az`, `azd`, `fab`,
Docker-in-Docker, and everything in [`requirements.txt`](requirements.txt).

1. **Code → Codespaces → Create codespace on main.** Wait for post-create to finish.
2. Sign in: `az login --use-device-code` (use your workshop account).
3. Copy the values sheet the facilitator shows (project endpoint) into `content/assets/.env`, and set `INITIALS`.
4. Open a lab script in `content/assets/` and run it cell by cell (`# %%`).

</details>

<details>
<summary><strong>Option B · Local machine</strong></summary>

Windows (PowerShell):

```powershell
python -m venv .venv ; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
az login
$env:PYTHONIOENCODING = "utf-8"
```

macOS / Linux:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
az login
```

Windows on ARM: some wheels are x64-only. Use an x64 Python, or Codespaces.

</details>

## Facilitators

<details>
<summary><strong>Run of show, admin and cost</strong></summary>

- [Facilitator run of show](foundry-workshop-plan.md): the 9:00–5:30 agenda, checkpoint gates, backup plans and demo prompts.
- [Admin setup](content/admin/ADMIN-SETUP.md): timeline T-10 → T+1, cost table, RBAC, troubleshooting.
  [Tenant bootstrap](content/admin/TENANT-BOOTSTRAP.md): one-time tenant, Fabric and lab-account setup.
- Scripts: [preflight](scripts/preflight.sh), [provision](scripts/provision.sh), [cost guardrails](scripts/cost-guardrails.sh),
  [Fabric capacity](scripts/capacity.sh), [seed attendees](scripts/seed-attendees.sh), [teardown](scripts/teardown.sh).
- [Rahim's story](content/narrative/rahim.md): one chapter per lab, every beat tagged by seat and source.
- [Prompt bank](content/prompts/test-prompts.json): the single source of truth for every prompt in the labs, keys and demos.
- [Answer keys](content/answer-keys/): facilitator reference answers for each checkpoint (participants compare with the Expected output block on each lab page).
- [Fabric bridge inputs](content/fabric/): ontology blueprint, data-agent instructions, Mei's question bank.
- Deck: `deck/LiveWell-Foundry-Workshop-Day1.pptx` (built by `deck/build_deck.py`).
- Proof and demo kit (`pip install -r requirements-demos.txt`):
  [smoke test](scripts/smoke-test.py) (end-to-end check of the live environment, run T-1 and on the morning),
  [demo agents](demos/create-demo-agents.py) (the five `livewell-demo-*` agents and the `livewell-eval` dataset),
  [screenshots](demos/capture-screenshots.py) (fills the portal-track 📸 slots; `--list-missing`, `--link`),
  [demo videos](demos/record-demos.py) (one captioned walkthrough per lab, not committed), and the
  [dry-run template](demos/DRY-RUN-TEMPLATE.md).

</details>

<details>
<summary><strong>Repository layout</strong></summary>

```
content/
  config/         workshop.yaml (names, models, modes, IDs) + glossary.yaml
  data/           resident360/ (kit data + generated), citizens.json, activities.json, intake/, flyer-injected.md
  knowledge/      livewell-guides/ (11 guides, markdown + PDF) for Foundry IQ
  labs/           lab pages, Fabric step, bridge spotlight, Portal Track
  narrative/      rahim.md
  prompts/        test-prompts.json, coach-instructions.md
  answer-keys/    facilitator reference answers per checkpoint
  fabric/         ontology blueprint, data-agent instructions, question bank
scripts/          generators (gen-activity.py, gen-citizens.py), r360.py, check-content.py, smoke-test.py, build-guides-pdf.py
demos/            demo agents, screenshot capture, demo recorder (portal.py, scenes.py), DRY-RUN-TEMPLATE.md
deck/             build_deck.py + the pptx
```

</details>

<details>
<summary><strong>Data, licence and assumptions</strong></summary>

- All data is synthetic. Resident 360 data is vendored from the MIT-licensed
  [resident-360-data-workshop](https://github.com/stellistic/resident-360-data-workshop) kit; see [NOTICE.md](NOTICE.md).
- Rebuild generated data: `python scripts/gen-activity.py`, then `python scripts/gen-citizens.py`
  (both support `--check`). Validate all content: `python scripts/check-content.py`.
- Design decisions and open values: [ASSUMPTIONS.md](ASSUMPTIONS.md). Tool and SDK pins: [versions.md](versions.md). History: [CHANGELOG.md](CHANGELOG.md).
- Licence: [MIT](LICENSE).

</details>
