# versions.md: pinned tools, SDKs and preview surfaces

Last checked: 2026-09-28 (Phase 1). Re-check before each delivery with `scripts/admin/preflight.sh`,
which comes in Phase 2.

## Participant / facilitator tooling

| Tool | Pin | Why |
|---|---|---|
| Python | 3.13 (devcontainer); 3.12+ works locally | Matches Foundry SDK support matrix |
| uv | latest | Fast env creation in Codespaces |
| Azure CLI (`az`) | ≥ 2.75 | `az cognitiveservices`, `az role assignment` |
| Azure Developer CLI (`azd`) | ≥ 1.31 (1.34 available) | `azd provision`, `azd down --purge` |
| Fabric CLI (`fab`) | `ms-fabric-cli==1.7.0` | Workspace, lakehouse, notebook, ontology import |
| Node | 20 LTS (demos only) | Playwright recorder |

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
| Fabric ontology (preview) and Ontology Agent | Phase 3 | Fabric data agent over the lakehouse tables |
| Hosted agents (Agent Framework) | Lab 4 optional | Prompt agent published to Teams / M365 |
| Foundry MCP server | Admin | `az` and SDK scripts |
