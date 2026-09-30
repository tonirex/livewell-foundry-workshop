// mcaps — dry-run environment (Antonia's MCAPS subscription).
// Differs from sponsor.bicepparam ONLY in: subscription (set in the azd env), capacity admins, caps, tags.
// Subscription 15715b5a-037a-4d59-bf60-2fa0986a3179 · tenant 108f6739-7d66-44bd-b535-c1812dab17b5
using '../main.bicep'

param environmentName = 'mcaps'
param location = readEnvironmentVariable('AZURE_LOCATION', 'swedencentral')
param principalId = readEnvironmentVariable('AZURE_PRINCIPAL_ID', '')
param principalType = readEnvironmentVariable('AZURE_PRINCIPAL_TYPE', 'User')

// Fabric capacity admins = UPNs of member accounts in the MCAPS tenant.
param fabricAdminMembers = [
  'admin@mngenvmcap761802.onmicrosoft.com'
]
param fabricBridge = bool(readEnvironmentVariable('FABRIC_BRIDGE', 'true'))
param projectMode = readEnvironmentVariable('MODE', 'shared-project')

// Caps (dry run: a single facilitator plus a handful of test accounts).
// Search: Basic in the main region by default. If the region is capacity-blocked for new search services
// (preflight check 7), set SEARCH_LOCATION (e.g. francecentral) or SEARCH_SKU=serverless in the azd env.
param searchSku = readEnvironmentVariable('SEARCH_SKU', 'basic')
param searchLocation = readEnvironmentVariable('SEARCH_LOCATION', '')
param fabricSku = 'F2'
param chatTpmCapThousands = 400
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
  'admin@mngenvmcap761802.onmicrosoft.com'
]

param extraTags = {
  purpose: 'dry-run'
  owner: 'antonia-chen'
}

// MCAPS policy "StorageAccount_PublicNetwork_Modify" forces publicNetworkAccess=Disabled unless this tag is
// present. ASSUMPTIONS.md 4.4.
param storagePolicyOptOutTag = {
  SecurityControl: 'Ignore'
}

// Allow = Entra-only public access so Lab 2 can publish evaluation runs; Deny = Search + trusted services only.
param storageNetworkDefaultAction = 'Allow'
