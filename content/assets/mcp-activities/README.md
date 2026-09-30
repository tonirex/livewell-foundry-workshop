# mcp-activities

Lab 3 tool server on Azure Container Apps (`ca-mcp-activities-<env>`), one container for two tools:

| Path | What | Used by |
|---|---|---|
| `/mcp` | FastMCP streamable HTTP: `find_activities` (read) and `register_interest` (write) over `content/data/activities.json` | MCP tool from project connection `livewell-activities-mcp` |
| `/openapi.json`, `/profile/{resident_id}` | OpenAPI 3.0 `get_citizen_profile` over `content/data/citizens.json`, **session resident only** (`me`; any other id gets 403) | Navigator OpenAPI tool `livewell_profile` |
| `/healthz` | Liveness plus activity and registration counts | `scripts/smoke-test.py`, facilitators |

Synthetic data, no authentication, registrations held in memory (gone when the app scales to zero).

## Deploy

```bash
azd deploy mcp-activities                     # remote ACR build; copies the two JSON files in first
python scripts/connect-tools.py               # project connection livewell-activities-mcp (+ values sheet URLs)
```

`MCP_URL` in the azd env is `https://<fqdn>/mcp`; the profile spec URL is `https://<fqdn>/openapi.json`
(both on `content/config/values.md`).

## Portal approval settings (Navigator, Lab 3)

In the agent's MCP tool (connection `livewell-activities-mcp`):

- `find_activities`: **no approval** (read-only lookup).
- `register_interest`: **approval required** (write). The coach must show the approval card and wait for the
  resident's "yes"; `lab3_hazy_indoor_signup` checks this.

Builder scripts set the same thing in code: `require_approval={"never": {"tool_names": ["find_activities"]}}`
style settings, so `register_interest` always asks.

## Run locally

```bash
PORT=8000 python content/assets/mcp-activities/server.py
curl localhost:8000/healthz
curl localhost:8000/profile/me
```
