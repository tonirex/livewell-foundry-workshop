# hosted-agent-example (Phase 4)

Lab 4 facilitator-only hosted agent `livewell-workshop-hosted` (protected prefix `livewell-workshop-`),
scaffolded with the azd AI agents extension and carrying an `rai_config` that points at the
`livewell-guardrails` policy.

Phase 2 provisions what it needs: the Foundry project, the model deployments, the ACR and the project's
AcrPull role. Phase 4 adds the agent code and deploys it with `azd deploy hosted-agent-example`.
