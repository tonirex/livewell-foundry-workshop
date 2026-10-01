# hosted-agent-example · `livewell-workshop-hosted` (Lab 4, facilitator only)

The Lab 4 sequential team packaged as a **Foundry hosted agent** with the Microsoft Agent Framework:

```text
request -> resident profile -> Nutrition -> Activity -> Coach -> one evidence JSON reply
```

| File | What it is |
|---|---|
| `main.py` | The workflow (`SequentialBuilder`) served on the Responses protocol by `ResponsesHostServer`. |
| `livewell.json` | Instructions, tool connections and reply schema. **Generated** by `python scripts/gen-schemas.py` from `content/prompts/coach-instructions.md` and `livewell_common.py`; `check-content.py` fails if it is stale. |
| `requirements.txt` | Pinned Agent Framework packages (tested versions, see `versions.md`). |
| `.env.sample` | For local runs only. |
| `.agentignore` | Kept out of the deploy zip. |

The service block is `livewell-workshop-hosted` in the root `azure.yaml` (code deploy: Foundry builds the
image, no Docker or ACR push). The name has the protected `livewell-workshop-` prefix, so `--cleanup` and
`make clean-agents` never delete it.

## What it does

* **Resident profile.** A first workflow step reads `/profile/me` from the activities app (the session resident
  only, the same rule as the Navigator profile tool) and puts a one-line summary in front of the request. The
  resident_id never enters the conversation.
* **Nutrition and Activity** use the same project connections as the lab agents: the knowledge-base MCP
  endpoint (`livewell-guides-kb-mcp`) and `find_activities` (`livewell-activities-mcp`; `register_interest` is
  not allowed). Foundry calls the MCP servers, not the container.
* **Coach** merges both answers into the Lab 3 evidence JSON; the schema only accepts real guide ids.
* A `text_only` agent middleware passes earlier answers to each agent as plain text (another agent's MCP call
  items can make a model call fail). Every inner call has `store: False`.
* **Guardrail.** The agent carries `livewell-guardrails` (`rai_config` = its full resource ID), which screens
  requests at the agent endpoint: a blocked prompt fails fast with HTTP 400 `content_filter` (`--verify`). The
  model calls the team makes inside the container go straight to the project deployments, which run the platform
  default `Microsoft.DefaultV2` (ASSUMPTIONS.md 6.1).

## Deploy (facilitator)

Needs **Foundry Project Manager** (or Owner) on the project, plus the right to create role assignments on it
(Owner or User Access Administrator), because the postdeploy hook grants the agent identity a role.
Participants are Foundry User and cannot publish. Run from the repo root with the repo `.venv` active (the hook
runs `python scripts/hosted-postdeploy.py`) and the workshop azd env selected.

```bash
azd env get-values | grep -E "AZURE_AI_PROJECT_(ENDPOINT|ID)|AZURE_AI_MODEL_DEPLOYMENT_NAME|AZURE_TENANT_ID"
azd env set AZURE_TENANT_ID "$(az account show --query tenantId -o tsv)"   # once per env, if missing
python scripts/gen-schemas.py --check                                    # livewell.json is current
azd deploy livewell-workshop-hosted --no-prompt
azd ai agent show livewell-workshop-hosted --output json                 # status active
```

What the deploy does:

1. azd uploads the folder (minus `.agentignore`), Foundry builds it and publishes version *N* (a few minutes).
2. The postdeploy hook `scripts/hosted-postdeploy.py`:
   * grants the agent identity (an Entra identity Foundry creates on the first deploy) **Foundry User** on the
     project, so the container can call the models and read the tool connections;
   * publishes version *N+1*: same code zip and definition plus `rai_config = livewell-guardrails`. azure.yaml
     cannot carry the policy itself: the extension does not expand `${VAR}` in `policies` for hosted agents
     and the service needs the full, tenant-specific resource ID.

Each deploy therefore adds two immutable versions; calls by name use the latest. After the first deploy
allow about 2 minutes for the role to propagate before invoking.

## Smoke test

```bash
azd ai agent invoke livewell-workshop-hosted "Plan my week: what to eat for my glucose, and one indoor morning activity near Woodlands."
python scripts/hosted-postdeploy.py --verify     # RBAC + guardrail present, and a blocklisted prompt is blocked
```

Expect one JSON object (`advice`, `confidence`, `supporting_guides` with at least one `lg-...` id,
`rationale`, `personalisation_flags`) that suggests an indoor morning activity; the first call after a
deploy includes a cold start (about a minute). Participants run the same check from Lab 4 section 7
(`lab4_multiagent.py`), which calls the agent's own endpoint with Foundry User rights and also confirms the
agent's guardrail is `livewell-guardrails`.

`--verify` sends the Lab 2 `lab2_medication_double` prompt, which the medication-dosage blocklist stops: the
call must fail with HTTP 400 `content_filter`. Run it after every deploy.

## Run locally (optional)

```bash
cd content/assets/hosted-agent-example
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
python -m pip install uv                                 # optional: faster installs
cd ../../..
azd ai agent run livewell-workshop-hosted --no-client    # installs requirements.txt, serves localhost:8088
azd ai agent invoke livewell-workshop-hosted --local "Plan my week: what to eat for my glucose, and one indoor morning activity near Woodlands."
```

Local runs use your `az login` identity.

## Cost and teardown

A hosted agent bills compute (0.5 vCPU / 1 GiB here) only while a session is active, plus the model tokens of
four steps per request. Delete it after the workshop with `azd ai agent delete livewell-workshop-hosted` or in
the portal (Agents > livewell-workshop-hosted > Delete); `scripts/teardown.sh` removes the whole project.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `session_not_ready` / 424 | Read the container log: `azd ai agent sessions list --agent-name livewell-workshop-hosted`, then `azd ai agent monitor livewell-workshop-hosted --session-id <id> --tail 100`. A cold start clears in about a minute; retry. |
| `PermissionDenied ... connections/read` (or 401/403 on model calls) in the log | The agent identity has no Foundry User on the project: run `python scripts/hosted-postdeploy.py`, wait 2 minutes, retry with `--new-session`. |
| postdeploy hook: `No module named ...` | Activate the repo `.venv` before `azd deploy` (the hook uses `python` from `PATH`). |
| `code_configuration is not supported with application/json` | You called `create_version` on a code-deployed agent; use `create_version_from_code` (the hook does). |
| Reply is prose, not JSON | `livewell.json` is stale: run `python scripts/gen-schemas.py` and redeploy. |
| Harmful prompt is answered | `python scripts/hosted-postdeploy.py --verify`; it re-attaches the guardrail if the latest version lacks it. |
| `Hosted agents can only be called through the agent endpoint` | Call `{project}/agents/livewell-workshop-hosted/endpoint/protocols/openai` (`get_openai_client(agent_name=...)`), not the project endpoint with `agent_reference`. `lw.ask` does this for you. |
| `Workflow is already running` | One request at a time per session; retry, or start a new session with `--new-session`. |
| `uv` TLS handshake errors in `azd ai agent run` | Corporate TLS inspection: uninstall `uv` from the venv and remove it from `PATH`; azd falls back to pip. |
