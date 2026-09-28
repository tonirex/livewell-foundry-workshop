// Azure AI Search — one shared service for the whole cohort (Basic by default; never S1+).
param location string
param tags object
param name string

@description('basic (default), free, or serverless (Serverless Developer tier, preview). Standard tiers are blocked by design (SPEC.md §13).')
@allowed([
  'basic'
  'free'
  'serverless'
])
param sku string = 'basic'

@description('Semantic ranker plan. free = 1,000 queries/month, enough for the workshop.')
@allowed([
  'disabled'
  'free'
  'standard'
])
param semanticSearch string = 'free'

@description('Agentic retrieval (knowledge base) billing plan. Leave on free until the allowance is hit (SPEC.md §8.3).')
@allowed([
  'free'
  'standard'
])
param knowledgeRetrieval string = 'free'

var isDedicated = sku == 'basic'

resource search 'Microsoft.Search/searchServices@2026-09-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: sku
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: union(
    {
      publicNetworkAccess: 'Enabled'
      disableLocalAuth: false
      authOptions: {
        aadOrApiKey: {
          aadAuthFailureMode: 'http401WithBearerChallenge'
        }
      }
    },
    isDedicated
      ? {
          replicaCount: 1
          partitionCount: 1
          hostingMode: 'Default'
          semanticSearch: semanticSearch
          knowledgeRetrieval: knowledgeRetrieval
        }
      : {}
  )
}

output id string = search.id
output name string = search.name
output endpoint string = 'https://${search.name}.search.windows.net'
output principalId string = search.identity.principalId
