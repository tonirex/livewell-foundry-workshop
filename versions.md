# versions.md: pinned tools, SDKs and preview surfaces

Last checked: 2026-09-29 (Phase 2). Re-check before each delivery with `bash scripts/preflight.sh <env>`.

## Participant / facilitator tooling

| Tool | Pin | Why |
|---|---|---|
| Python | 3.13 (devcontainer); 3.12+ works locally | Matches Foundry SDK support matrix |
| uv | latest | Fast env creation in Codespaces |
| Azure CLI (`az`) | ≥ 2.75 | `az cognitiveservices`, `az role assignment` |
| Azure Developer CLI (`azd`) | ≥ 1.31 (1.34 available) | `azd provision`, `azd down --purge` |
| Fabric CLI (`fab`) | `ms-fabric-cli==1.7.0` | Workspace, lakehouse, notebook, ontology import |
| Node | 20 LTS (demos only) | Playwright recorder |

Verified end to end on 2026-09-29 (Phase 2, `mcaps` environment): az 2.87.0, azd 1.34.2, Bicep 0.47.16,
azd extension `azure.ai.agents` 1.0.0-beta.17, fab 1.7.0, Git Bash (Git for Windows) on Windows ARM64.
Phase 3 (`scripts/fabric/deploy.sh mcaps`) verified on 2026-09-29 with the same tools.

## Azure resource API versions (Bicep, `infra/`)

| Resource type | API version |
|---|---|
| `Microsoft.CognitiveServices/accounts` (+ `/deployments`, `/projects`, `/projects/connections`) | 2025-06-01 |
| `Microsoft.Search/searchServices` | 2026-09-01-preview (create); 2025-05-01 (`existing` in RBAC) |
| `Microsoft.Fabric/capacities` | 2023-11-01 |
| `Microsoft.Consumption/budgets` | 2023-11-01 |
| `Microsoft.App/managedEnvironments`, `Microsoft.App/containerApps` | 2024-03-01 |
| `Microsoft.ContainerRegistry/registries` | 2023-07-01 |
| `Microsoft.Storage/storageAccounts` | 2023-05-01 |
| `Microsoft.OperationalInsights/workspaces` | 2023-09-01 |
| `Microsoft.Insights/components` | 2020-02-02 |
| `Microsoft.ManagedIdentity/userAssignedIdentities` | 2023-01-31 |
| `Microsoft.Authorization/roleAssignments` | 2022-04-01 |

Management-plane REST calls in `scripts/` use the same versions (Search usages and name check 2025-05-01,
Cost Management query 2023-11-01, Fabric capacity suspend/resume 2023-11-01). Fabric data plane: REST `v1`.

## Fabric REST surfaces (Phase 3, `scripts/fabric/`)

| Surface | Endpoint | Status |
|---|---|---|
| Items, lakehouse tables, job scheduler | `/v1/workspaces/{ws}/items`, `…/lakehouses/{id}/tables`, `…/items/{id}/jobs/{type}/instances` | GA |
| Ontology item (create / updateDefinition / getDefinition) | `/v1/workspaces/{ws}/items` with `type: Ontology` (Lab 28 part layout) | Preview |
| Graph model refresh | `…/items/{graph}/jobs/refreshGraph/instances` | Preview |
| Graph GQL query (instance check) | `/v1/workspaces/{ws}/graphModels/{id}/executeQuery?beta=true` | Beta |
| Data agent management | `/v1/workspaces/{ws}/dataAgents/{id}/staging/{settings,datasources,…/elements,publish}` | Preview; the same calls as `fabric-data-agent-sdk` 0.1.32a0 (not installed) |
| Data agent MCP endpoint | `/v1/mcp/workspaces/{ws}/dataagents/{id}/agent`, MCP protocol 2025-06-18 | Preview |
| OneLake file read | `https://onelake.dfs.fabric.microsoft.com/{ws}/{item}/Files/…` (x-ms-version 2023-11-03) | GA |

## Python packages (Builder rail and scripts)

| Package | Pin | Notes |
|---|---|---|
| `azure-ai-projects` | `>=2.0.0` (2.7.0 current) | New Agents API (`agents.create_version`, Responses) |
| `azure-identity` | `>=1.19` | `DefaultAzureCredential` / device code |
| `openai` | `>=1.99` | Responses client from `project.get_openai_client()` |
| `azure-search-documents` | `==12.1.0b1` | Foundry IQ knowledge base API (per microsoft/iq-series); 12.1.0b2 exists but is not validated |
| `azure-ai-evaluation` | `>=1.10` (1.18.7 current) | Groundedness, relevance, safety evaluators |
| `agent-framework` | `>=1.0` (1.19.0 current) | Hosted agent (Lab 4 optional) |
| `mcp` | `<2` | FastMCP activities server; mcp 2.x changed the server API (casepal lesson) |
| `pyyaml`, `python-pptx`, `fpdf2`, `jupytext` | see `requirements.txt` | Content build (deck, guide PDFs, notebooks) |

## Models

Deployment names equal model names (see `models:` in `content/config/workshop.yaml`).

| Role | Model | SKU | Region |
|---|---|---|---|
| Default | model-router | GlobalStandard, 100K TPM cap | swedencentral (availability is checked in Phase 2 preflight) |
| Fallback | gpt-4.1-mini | GlobalStandard, 100K TPM cap | swedencentral |
| Embeddings | text-embedding-3-large | GlobalStandard | swedencentral |

PTU deployments and partner models are never used.

## Preview surfaces (may change; each has a fallback in `foundry-workshop-plan.md`)

| Surface | Used in | Fallback |
|---|---|---|
| Foundry IQ knowledge bases (agentic retrieval) | Lab 1 | Classic Azure AI Search tool on the same index |
| Model router | Lab 0 | Fixed `gpt-4.1-mini` deployment |
| Guardrails (new Foundry portal) and custom blocklists | Lab 2 | Content filter on the deployment; prebuilt demo agent `livewell-demo-guarded` |
| Prompt shields / indirect-attack detection | Lab 2 | Instruction-level defence plus a facilitator demo |
| Memory (Foundry Agent Service) | Lab 3 | Conversation-scoped preferences in instructions |
| Connected agents / multi-agent | Lab 3 | Single agent with specialist instruction blocks |
| Fabric IQ tool (Ontology Agent via OneLake Catalog) | Fabric step, Lab 4 | Facilitator-only demo from `demos/`; pre-computed numbers from `scripts/r360.py` |
| Fabric ontology (preview), graph model and data agent over the ontology | Phase 3 | Fabric data agent over the lakehouse tables |
| Hosted agents (Agent Framework) | Lab 4 optional | Prompt agent published to Teams / M365 |
| Foundry MCP server | Admin | `az` and SDK scripts |
