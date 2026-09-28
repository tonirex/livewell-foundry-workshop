# mcp-activities (Phase 4)

Lab 3 activities MCP server: FastMCP over streamable HTTP at `/mcp`, serving `content/data/activities.json`.

Phase 2 provisions its home: the Container App `ca-mcp-activities-<env>` (placeholder image, tagged
`azd-service-name: mcp-activities`), the ACR it pulls from and the user-assigned identity with AcrPull.
Phase 4 adds `server.py`, `requirements.txt` and `Dockerfile`, then `azd deploy mcp-activities`.
