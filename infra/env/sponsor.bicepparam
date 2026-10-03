// sponsor — delivery environment (Azure sponsorship subscription, separate Entra tenant).
// Differs from mcaps.bicepparam ONLY in: subscription (set in the azd env), capacity admins, caps, tags.
// Subscription TODO · tenant TODO (fill in content/config/workshop.yaml → environments.sponsor)
using '../main.bicep'

param environmentName = 'sponsor'
param location = readEnvironmentVariable('AZURE_LOCATION', 'swedencentral')
param principalId = readEnvironmentVariable('AZURE_PRINCIPAL_ID', '')
param principalType = readEnvironmentVariable('AZURE_PRINCIPAL_TYPE', 'User')

// Fabric capacity admins = UPNs of MEMBER accounts in the sponsor tenant (not guests).
// TODO: replace with the facilitator UPN(s) created by content/admin/TENANT-BOOTSTRAP.md.
param fabricAdminMembers = [
  'TODO-facilitator@TODO.onmicrosoft.com'
]
param fabricBridge = bool(readEnvironmentVariable('FABRIC_BRIDGE', 'true'))
param projectMode = readEnvironmentVariable('MODE', 'shared-project')

// Caps (delivery: 6 attendees on one shared project, one shared search service). Quota Tier 0 limits:
// gpt-5-mini 500K, gpt-4.1-mini 200K, text-embedding-3-small 1M TPM (ASSUMPTIONS.md 9.1).
// Search: Basic in the main region by default. If the region is capacity-blocked for new search services
// (preflight check 7), set SEARCH_LOCATION (e.g. francecentral) or SEARCH_SKU=serverless in the azd env.
param searchSku = readEnvironmentVariable('SEARCH_SKU', 'basic')
param searchLocation = readEnvironmentVariable('SEARCH_LOCATION', '')
param fabricSku = readEnvironmentVariable('FABRIC_SKU', 'F2')
param chatTpmCapThousands = 400
param toolsTpmCapThousands = 200
param embeddingTpmCapThousands = 100
param mcpMinReplicas = int(readEnvironmentVariable('MCP_MIN_REPLICAS', '0'))
param mcpImage = readEnvironmentVariable('SERVICE_MCP_ACTIVITIES_IMAGE_NAME', '')

param budgetAmountUsd = 300
param budgetStartDate = readEnvironmentVariable('BUDGET_START_DATE', '')
param budgetAlertThresholdsUsd = [
  150
  300
]
param budgetContactEmails = [
  'TODO-facilitator@TODO.onmicrosoft.com'
]

param extraTags = {
  purpose: 'delivery'
  owner: 'antonia-chen'
  customer: 'hpb'
}

// Only if the sponsor tenant has a policy forcing storage publicNetworkAccess=Disabled (see mcaps.bicepparam).
param storagePolicyOptOutTag = {}

// Allow = Entra-only public access so Lab 2 can publish evaluation runs; Deny = Search + trusted services only.
param storageNetworkDefaultAction = 'Allow'
