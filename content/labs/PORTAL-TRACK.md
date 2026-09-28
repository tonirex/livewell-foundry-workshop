# LiveWell Coach — Portal track (🟢 Navigator)

This portal-only track is for 🟢 Navigator participants who want a click-by-click, screenshot-led path through the workshop. You will use the Microsoft Foundry portal only: no code, no terminal, no SDK, and no notebooks.

Screenshots are captured later in Phase 5 by the `demos/` screenshot capture with Playwright. Until those files exist, every walkthrough uses text-only screenshot slots so link checkers do not fail.

## Naming rules

Your portal agent is `livewell-<initials>` and is reused from Lab 0 through Lab 3. Use your own initials, keep the name short, and never touch facilitator demo agents named `livewell-demo-*` or protected workshop agents named `livewell-workshop-*`.

## Walkthroughs

| # | Walkthrough | Capability | Time | Guide |
|---|---|---|---:|---|
| 0 | Setup & first agent | Foundry portal, prompt agent, model-router, traces | 15 min | [Lab 0 portal](lab-00-portal.md) |
| 1 | Agents & Knowledge | Foundry IQ knowledge base, citations, JSON response | 40 min | [Lab 1 portal](lab-01-portal.md) |
| 2 | Guardrails, Evaluations & Tracing | RAI policy, red flags, traces, version comparison | 40 min | [Lab 2 portal](lab-02-portal.md) |
| 3 | Tools, MCP & Memory | OpenAPI, MCP approvals, memory, optional Fabric IQ | 40 min | [Lab 3 portal](lab-03-portal.md) |
| 4 | Multi-agent & Hosted deploy | Facilitator watch-along: hosted agent, versions, traces, RBAC | 30 min | [Lab 4 portal](lab-04-portal.md) |

## Screenshot slot convention

Each lab step has a screenshot slot in this exact format:

> 📸 **Screenshot slot** · `screenshots/lab-01/03-connect-foundry-iq.png` · Knowledge panel with livewell-guides-kb selected

Rules for screenshot authors:

- Keep screenshot paths relative to `content/labs/`.
- Use `screenshots/lab-0N/NN-short-slug.png`.
- Do not convert slots into markdown images or links until Phase 5 assets exist.
- Capture only names shown in [workshop.yaml](../config/workshop.yaml), never tenant IDs, subscription IDs, endpoints, keys, or real email domains.

