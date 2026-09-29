# ADMIN-SETUP — facilitator runbook (T-10 → T+1)

Everything a facilitator runs to stand up, operate and tear down one LiveWell Coach workshop environment.
The resources, names and costs come from [SPEC.md](../../SPEC.md) §8, §12.1 and §13. The one config file is
[workshop.yaml](../config/workshop.yaml). The sponsored-tenant variant is in [TENANT-BOOTSTRAP.md](TENANT-BOOTSTRAP.md).

- [Who needs what](#who-needs-what)
- [Timeline](#timeline)
- [Cost table](#cost-table)
- [What not to leave running](#what-not-to-leave-running)
- [RBAC model and gotchas](#rbac-model-and-gotchas)
- [Backup plans](#backup-plans)
- [Troubleshooting provisioning](#troubleshooting-provisioning)
- [Script reference](#script-reference)

## Who needs what

| Who | Needs | Why |
|---|---|---|
| Facilitator (runs the scripts) | **Owner** on the subscription (or Contributor + User Access Administrator) | The template creates role assignments |
| Facilitator | **Fabric Administrator** (Entra role) and a Fabric licence (Free is enough; sign in once at app.fabric.microsoft.com) | Tenant settings, capacity admin, `scripts/fabric/deploy.sh` |
| Facilitator | Listed in `fabricAdminMembers` in `infra/env/<env>.bicepparam` | Capacity admin in the Fabric admin portal |
| Whoever creates lab accounts | **User Administrator** (Privileged Role Administrator for the break-glass role) | [create-lab-users.sh](../../scripts/tenant/create-lab-users.sh) |
| Attendee | Nothing up front: [seed-attendees.sh](../../scripts/seed-attendees.sh) grants it | See [RBAC model](#rbac-model-and-gotchas) |

Tools: Azure CLI, Azure Developer CLI **1.34 or later** (`azd version`), Python 3.11+ with
`pip install -r requirements.txt`, Fabric CLI (`pip install ms-fabric-cli`, Phase 3), and bash. The Codespace
has all of them. On Windows, use Git Bash (`bash scripts/preflight.sh mcaps`).

Sign in once per shell:

```bash
az login --tenant <tenant-id>             # tenant ID: workshop.yaml environments.<env>.tenant_id
azd auth login --tenant-id <tenant-id>
fab auth login                            # Phase 3 onwards
```

## Timeline

### T-10: quota requests

```bash
azd env new mcaps --subscription <subscription-id> --location swedencentral   # once per environment
bash scripts/preflight.sh mcaps
```

For every FAIL, preflight prints the quota-request link. Typical asks on a fresh subscription:

| Quota | Needed | Where |
|---|---|---|
| Fabric capacity units in `swedencentral` | 2 CU (F2) | Azure portal → Quotas → Microsoft Fabric |
| `model-router` Global Standard | 100K TPM | Foundry portal → Management center → Quota |
| `gpt-4.1-mini` Global Standard | 100K TPM | Same |
| `text-embedding-3-large` Global Standard | 100K TPM | Same |
| Azure AI Search Basic in `swedencentral` | 1 service | Usually available; preflight checks it |

### T-7: tenant settings and preflight green

1. Fabric admin portal → Tenant settings, as listed in [TENANT-BOOTSTRAP.md](TENANT-BOOTSTRAP.md#fabric-tenant-settings).
   Allow up to an hour to propagate.
2. Lab accounts, if the tenant does not have them yet:
   `bash scripts/tenant/create-lab-users.sh mcaps`. Passwords go to `.azure/mcaps/lab-accounts.csv` (gitignored).
3. `bash scripts/preflight.sh mcaps` must end with **all checks passed**. Warnings are fine.
   Accepted warnings are the portal red-teaming region (red teaming runs through the SDK instead) and a missing `fab`
   before Phase 3.

### T-3: build the environment

About 1.5 h end to end.

| Step | Command | Time | Done when |
|---|---|---|---|
| 1 Provision | `bash scripts/provision.sh mcaps --what-if` | ≈ 15 min | "provisioned mcaps" and `content/config/values.md` written |
| 2 Guardrails | `bash scripts/cost-guardrails.sh mcaps` | 1 min | All PASS; budget alerts at US$150 and US$300 listed |
| 3 Resident 360 on Fabric | `bash scripts/fabric/deploy.sh mcaps` | ≈ 17–20 min | 6 tables, ontology 4/4 with instances, graph refresh Completed, data agent published |
| 4 Fabric IQ connection | Runbook step in [fabric-step.md](../labs/fabric-step.md) (Phase 4 helper) | 2 min | `FABRIC_IQ_CONNECTION_ID` in `.azure/mcaps/.env` |
| 5 Knowledge base | `python content/assets/build-kb.py` (Phase 4) | 5 min | `livewell-guides-kb` answers with a citation |
| 6 MCP server | `azd deploy mcp-activities` (Phase 4) | 5 min | `MCP_URL` responds |
| 7 Attendees | `bash scripts/seed-attendees.sh mcaps --lab-accounts` | 2 min | Every row shows `added` or `exists` |
| 8 Proof | `python scripts/smoke-test.py` and `python scripts/validate-narrative.py` (Phase 5 / 3b) | 10 min | Both green |
| 9 Pause | `bash scripts/capacity.sh suspend mcaps` | 1 min | Capacity `Paused` |

> **Always provision through `scripts/provision.sh`.** azd reads `infra/main.bicepparam` *before* its
> preprovision hook runs. The script runs `scripts/select-params.py` first, which copies
> `infra/env/<env>.bicepparam` into place, records your principal ID and creates the resource group. A bare
> `azd provision` still works once that file exists. If the hook had to regenerate anything, it stops with "re-run"
> so a stale file can never deploy the wrong environment.

Re-run step 7 after step 3 so that attendees also get **Viewer** on the Fabric workspace, which gives read access to
the data agent.

#### Step 3 in detail: `scripts/fabric/deploy.sh`

Needs `az login` and `fab auth login` as the facilitator, the capacity **Active** (`scripts/capacity.sh resume`), and the
tenant settings above. Every step checks before it creates, so re-running is safe. After a failure, resume with
`--from NN`. Use `--only NN` for one step and `--skip-upload` to reuse the files already in OneLake.

| Step | What it does | Typical time (F2) |
|---|---|---|
| 10 workspace | `HPB Resident 360` on the capacity; facilitators as workspace Admin | 1 min |
| 20 lakehouse-load | `lh_resident360`; uploads the kit files and `r360.py` (one file at a time); imports and runs `load_resident360`; checks the 6 tables, Rahim and the headline answer against the local build | 6–8 min |
| 30 ontology | `resident_ontology` from `content/fabric/ontology.blueprint.yaml` (create, or update in place). Either one starts a graph refresh | 2 min first time, then < 1 min |
| 35 graph-refresh | Waits for the refresh that step 30 started (or starts one) and counts nodes and edges with GQL | 8–9 min |
| 40 data-agent | `Resident360 Ontology Agent`: instructions, ontology source, **all entity types selected**, publish | 1 min |
| 90 write-env | `FABRIC_*` IDs and URLs into `.azure/<env>/.env` | 1 min |

Then check the agent from the command line (30–45 s per answer):

```bash
python scripts/fabric/ask.py "Which regions have the highest share of disengaged residents?"
# North 60/300 = 20.0%, then West 17.1%, Central 13.1%, East 11.7%, North-East 8.3%
python scripts/gen-citizens.py --from-onelake --check    # citizens.json agrees with the lakehouse
```

| Symptom | Fix |
|---|---|
| Step 30: 403 `FeatureNotAvailable` | Tenant setting **Users can create Ontology (preview) items** is off, or has not propagated yet (wait 15–60 min) |
| Data agent answers "There's content here that I can't work with" and then gives numbers | Its entity types are not selected, so the numbers are invented. Run `deploy.sh <env> --only 40`, then check again |
| Data agent reports a backend graph error | The graph has not loaded yet. Run `deploy.sh <env> --only 35` |
| Step 20 fails inside the notebook | Open `load_resident360` in the workspace to see the failing cell. The capacity must be Active |
| You changed the blueprint | `deploy.sh <env> --from 30`. The ontology is updated in place, then refreshed and republished |

### T-1: dry run

- `bash scripts/capacity.sh resume mcaps`, then run the whole day with a lab account in a private browser window.
- Record the demos (Phase 5 `demos/`) and fill in `demos/DRY-RUN-<date>.md`.
- `bash scripts/cost-guardrails.sh mcaps --max-usd 150`, then `bash scripts/capacity.sh suspend mcaps`.

### T-0: workshop day

```bash
bash scripts/capacity.sh resume mcaps                    # ~1 min; Fabric step + bridge spotlight need it
MCP_MIN_REPLICAS=1 bash scripts/provision.sh mcaps --skip-preflight   # no MCP cold starts during labs
python scripts/render-values.py mcaps                    # values sheet -> content/config/values.md
```

Put `content/config/values.md` on screen: the project endpoint, agent names, lab-account pattern and Wi-Fi.
Lab pages only ever use names.

### T+1: teardown

```bash
bash scripts/teardown.sh mcaps          # asks you to type the env name; --yes for scripts
```

This deletes the Fabric workspace, runs `azd down --purge` (resource group, Fabric capacity, budget, and purge of
the soft-deleted Foundry account), then verifies that nothing tagged `workshop=livewell env=mcaps` remains.
Lab accounts stay; remove them with `bash scripts/tenant/create-lab-users.sh mcaps --delete`.
Between sessions use `bash scripts/teardown.sh mcaps --pause-only` (pauses the capacity).

## Cost table

US$ list prices, September 2026 (SPEC.md §13). The cohort is 20 people × 150 runs.

| Line | Low (gpt-4.1-mini, Basic search, facilitator red team) | High (gpt-4.1, S1, Bing $35/1k) |
|---|---:|---:|
| Model tokens (20 × 150 runs × 3k in / 500 out, ×2 buffer) | 12 | 60 |
| Quality evaluations (model tokens, no surcharge) | 4 | 4 |
| Red teaming / safety evals (AI evaluations meter $20/$60 per 1M; 5 scans × 50 prompts × 4 strategies) | 42 | 42 |
| Azure AI Search, 120 h | 12 | 40 |
| Semantic ranker, Bing, Code Interpreter, hosted agents, ACR, storage/App Insights | ~12 | ~18 |
| **Total** | **≈ 83** | **≈ 166** |
| Every participant runs a full red-team scan | +126 | → ≈ 292 |
| Fabric F2, 16 h active (≈ $0.36/h; ≈ $259/month if left on) | +6 | +6 |

Controls built into the template and checked by [cost-guardrails.sh](../../scripts/cost-guardrails.sh):

- One shared search service and knowledge base. Twenty Basic services would cost about $1,475/month.
- `model-router` is the default deployment. Every deployment is Global Standard, capped at 100K TPM, with no PTU
  and no partner models.
- Red teaming is run by the facilitator. The participant "lite" run (10 prompts × 2 strategies) costs about $17 in total.
- Bing grounding is off: there is no connection.
- The budget alerts at US$150 and US$300 (actual spend) and emails the facilitators plus the subscription Owners and Contributors.
- The Fabric capacity is paused every night, and `teardown.sh` runs at T+1.
- The agentic-retrieval plan stays on Free, and the semantic ranker plan on Free.
- Log Analytics has a 1 GB/day ingestion cap.

Check spend at any time with `bash scripts/cost-guardrails.sh mcaps`, which shows month-to-date cost by resource
type. Cost Management lags by up to 24 h.

## What not to leave running

| Resource | Idle cost | Action |
|---|---|---|
| Fabric capacity `fablivewell<env>` | ≈ US$0.36/h (≈ $259/month) | `scripts/capacity.sh suspend` every evening; deleted by `teardown.sh` |
| Azure AI Search Basic `srch-livewell-<env>` | ≈ US$0.10/h (≈ $74/month) | Delete with `teardown.sh` at T+1; do not keep an environment "just in case" |
| MCP app with `MCP_MIN_REPLICAS=1` | A few US$/day | Re-provision with the default (0) after the workshop |
| ACR Basic | ≈ US$0.17/day | `teardown.sh` |
| Hosted agent (Lab 4 facilitator demo) | Container compute while running | Delete it after the demo |
| Red-team scans | $20–$60 per 1M evaluation tokens | Facilitator only; never loop them |
| Log Analytics / App Insights | Per GB ingested (capped at 1 GB/day) | `teardown.sh` |

## RBAC model and gotchas

| Principal | Role | Scope | Granted by |
|---|---|---|---|
| Facilitators | Foundry Project Manager | Foundry account | `infra/modules/rbac.bicep` |
| Facilitators | Foundry User | Project | `rbac.bicep` |
| Facilitators | Search Service Contributor + Search Index Data Contributor | Search service | `rbac.bicep` |
| Facilitators | Storage Blob Data Contributor, AcrPush | Storage, ACR | `rbac.bicep` |
| Project managed identity | Search Index Data Reader, AcrPull | Search, ACR | `rbac.bicep` |
| Search managed identity | Cognitive Services User, Storage Blob Data Reader | Foundry account, storage | `rbac.bicep` |
| MCP app identity | AcrPull | ACR | `infra/modules/containerapps.bicep` |
| Attendees | Foundry User | Project | `seed-attendees.sh` |
| Attendees | Search Index Data Reader | Search service | `seed-attendees.sh` |
| Attendees | Log Analytics Reader | Application Insights | `seed-attendees.sh` (Tracing tab) |
| Attendees | Fabric workspace Viewer (read on the data agent) | Fabric workspace | `seed-attendees.sh`, after Phase 3 |

Role IDs are built-in and the same in every tenant. They live only in `workshop.yaml` → `rbac_roles`.

Gotchas:

- **Foundry User cannot deploy models, create connections or publish hosted agents.** The facilitator
  pre-creates every deployment, connection (search, storage, ACR, App Insights, MCP, Fabric IQ) and the Lab 4
  hosted agent. Attendees only create agents, threads and evaluations.
- **The Fabric IQ connection needs Foundry Project Manager to create** and only lists *published* data agents.
  Attendees reuse it; they need Foundry User plus read on the data agent (workspace Viewer).
- **The Fabric IQ tool runs as the signed-in user** (no service principal at runtime). The attendee's
  Foundry account and Fabric account must be the same Entra identity in the same tenant.
- Role assignments take up to 5 minutes to apply. Attendees should sign out and back in to ai.azure.com if
  the project is missing.
- `azd down` removes every role assignment with the resource group. `seed-attendees.sh` must be re-run after
  each re-provision.
- Guests (B2B) must redeem the invitation before role assignments show up in the portal. Lab accounts are simpler.

## Backup plans

| Failure | Backup |
|---|---|
| Sign-in / Authenticator / RBAC | Pair with a neighbour on a shared screen while an operator re-runs `seed-attendees.sh`; the break-glass account signs in if Entra is the problem |
| Model quota exhausted / 429s | Switch agents to the `gpt-4.1-mini` deployment (fallback, separate quota); lower concurrency by pairing |
| Knowledge base missing or broken | Attach the static guides (`content/knowledge/*.md`) as file search on the agent; rebuild the KB during the break |
| Evaluators unavailable in region | Show the pre-captured trace and evaluation screenshots from the dry run (`demos/`) |
| MCP server down | Run `content/assets/mcp-activities` locally (`python server.py`) and expose it with a dev tunnel; update the connection URL |
| Fabric tool down / capacity not resumed | `scripts/capacity.sh resume`; if the data agent still fails, play the pre-recorded answer from the dry run (the Fabric step is optional) |
| Whole region degraded | The documented fallback is `northcentralus`: `PREFLIGHT_ACCEPT_FALLBACK=1`, set `AZURE_LOCATION`, then re-provision (≈ 1.5 h). Decide by T-1 |

## Troubleshooting provisioning

| Symptom | Fix |
|---|---|
| `azd provision` → "missing required inputs" | Run `bash scripts/provision.sh <env>`, which generates `infra/main.bicepparam` first |
| Preprovision hook says "re-run" | Expected after switching environments; run the same command again |
| Budget deployment fails with a start-date error | An existing budget cannot move its start month. `select-params.py` pins `BUDGET_START_DATE` in the azd env on first provision and `teardown.sh` clears it. If you deleted the resource group by hand, run `azd env set BUDGET_START_DATE ""` before re-provisioning |
| `FlagMustBeSetForRestore` / "soft-deleted" Foundry account | `az cognitiveservices account purge -n aif-livewell-<env> -g rg-livewell-workshop-<env> -l swedencentral` (`teardown.sh` does this) |
| Fabric capacity "admin members invalid" | `fabricAdminMembers` must be UPNs of **member** accounts in the same tenant (no guests) |
| Fabric API `UserNotLicensed` | Sign in once at app.fabric.microsoft.com with that account to get the free Fabric licence |
| Fabric capacity: "Tenant ... wasn't recognized by Microsoft Fabric" | The tenant has never signed up for Fabric. A tenant admin signs in once at app.fabric.microsoft.com, then re-run `provision.sh`. Until then, `azd env set FABRIC_BRIDGE false` provisions everything else |
| Search: `ResourcesForSkuUnavailable` | The region has no capacity for new search services (seen in swedencentral for Basic **and** serverless). `azd env set SEARCH_LOCATION francecentral` (fallback `uksouth`, `switzerlandnorth`) and re-provision. Only the search service moves; Foundry reaches it over its managed identity. Record the block in `region_matrix.capacity_notes.search` so preflight catches it |
| `agent definition not found for service hosted-agent-example` | The `azure.ai.agents` azd extension needs the inline agent definition in `azure.yaml` (kept in the repo; do not delete it) |
| Git Bash: paths like `C:/Program Files/Git/subscriptions/...` | Use the scripts; `scripts/lib/common.sh` sets `MSYS_NO_PATHCONV=1` |

## Script reference

| Script | What it does |
|---|---|
| [preflight.sh](../../scripts/preflight.sh) | Tools, subscription, region matrix, providers, Fabric CU quota, model quota, Search Basic, Fabric admin |
| [provision.sh](../../scripts/provision.sh) | Env + parameters + optional what-if + `azd provision` + values sheet |
| [cost-guardrails.sh](../../scripts/cost-guardrails.sh) | Asserts the §13 controls; month-to-date cost; `--pause-fabric`, `--max-usd N` |
| [capacity.sh](../../scripts/capacity.sh) | `status`, `suspend` or `resume` the Fabric capacity |
| [fabric/deploy.sh](../../scripts/fabric/deploy.sh) | Resident 360 on Fabric: workspace, lakehouse and load, ontology, graph refresh, data agent, env IDs; `--from`, `--only`, `--skip-upload` |
| [fabric/ask.py](../../scripts/fabric/ask.py) | Ask the published data agent a question over MCP; `--json` |
| [gen-citizens.py](../../scripts/gen-citizens.py) | `citizens.json` from the gold build; `--check`, `--from-onelake` |
| [seed-attendees.sh](../../scripts/seed-attendees.sh) | Lab accounts / file / guests → project, search, tracing and Fabric access; `--remove`, `--dry-run` |
| [render-values.py](../../scripts/render-values.py) | `.azure/<env>/.env` → `content/config/values.md` |
| [teardown.sh](../../scripts/teardown.sh) | Fabric workspace → `azd down --purge` → verify; `--pause-only` |
| [create-lab-users.sh](../../scripts/tenant/create-lab-users.sh) | 20 lab accounts + break-glass (Graph); `--delete`, `--reset-passwords` |
