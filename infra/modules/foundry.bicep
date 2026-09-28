// Microsoft Foundry resource (AIServices account) + project + model deployments + project connections.
param location string
param tags object
param accountName string
param projectName string

@description('Model deployments: Global Standard only, capacity = TPM cap in thousands. No PTU.')
param deployments deploymentType[]

param appInsightsId string
@secure()
param appInsightsConnectionString string
param searchId string
param searchEndpoint string
param storageId string
param storageBlobEndpoint string
param acrId string
param acrLoginServer string

param searchConnectionName string
param storageConnectionName string
param acrConnectionName string
param appInsightsConnectionName string

type deploymentType = {
  name: string
  model: {
    format: string
    name: string
    version: string
  }
  sku: {
    name: 'GlobalStandard'
    @minValue(1)
    @maxValue(200)
    capacity: int
  }
}

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: accountName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    allowProjectManagement: true
    customSubDomainName: accountName
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
      virtualNetworkRules: []
      ipRules: []
    }
    disableLocalAuth: true
  }
}

@batchSize(1)
resource modelDeployments 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = [
  for d in deployments: {
    parent: account
    name: d.name
    sku: d.sku
    properties: {
      model: d.model
      versionUpgradeOption: 'NoAutoUpgrade'
    }
  }
]

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: account
  name: projectName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: projectName
    description: 'LiveWell Coach workshop project (shared by all attendees).'
  }
  dependsOn: [
    modelDeployments
  ]
}

resource appInsightsConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-06-01' = {
  parent: project
  name: appInsightsConnectionName
  properties: {
    category: 'AppInsights'
    target: appInsightsId
    authType: 'ApiKey'
    isSharedToAll: true
    credentials: {
      key: appInsightsConnectionString
    }
    metadata: {
      ApiType: 'Azure'
      ResourceId: appInsightsId
    }
  }
}

resource searchConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-06-01' = {
  parent: project
  name: searchConnectionName
  properties: {
    category: 'CognitiveSearch'
    target: searchEndpoint
    authType: 'AAD'
    isSharedToAll: true
    metadata: {
      ApiType: 'Azure'
      ResourceId: searchId
      type: 'azure_ai_search'
    }
  }
}

resource storageConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-06-01' = {
  parent: project
  name: storageConnectionName
  properties: {
    category: 'AzureStorageAccount'
    target: storageBlobEndpoint
    authType: 'AAD'
    isSharedToAll: true
    metadata: {
      ApiType: 'Azure'
      ResourceId: storageId
    }
  }
}

resource acrConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-06-01' = {
  parent: project
  name: acrConnectionName
  properties: {
    category: 'ContainerRegistry'
    target: acrLoginServer
    authType: 'ManagedIdentity'
    isSharedToAll: true
    credentials: {
      clientId: project.identity.principalId
      resourceId: acrId
    }
    metadata: {
      ResourceId: acrId
    }
  }
}

output accountId string = account.id
output accountName string = account.name
output accountPrincipalId string = account.identity.principalId
output accountEndpoint string = account.properties.endpoint
output openAiEndpoint string = account.properties.endpoints['OpenAI Language Model Instance API']
output projectId string = project.id
output projectName string = project.name
output projectPrincipalId string = project.identity.principalId
output projectEndpoint string = project.properties.endpoints['AI Foundry API']
output searchConnectionId string = searchConnection.id
output appInsightsConnectionId string = appInsightsConnection.id
