// Container hosting for the Lab 3 activities MCP server (and a home for the Lab 4 hosted-agent image):
// ACR Basic + user-assigned identity (AcrPull) + Container Apps environment + placeholder app that
// `azd deploy mcp-activities` replaces with the real image (Phase 4).
param location string
param tags object
param acrName string
param identityName string
param environmentName string
param mcpAppName string
param logAnalyticsId string

@description('0 = scale to zero between sessions (cold start ~10 s). Set 1 on the workshop day.')
@minValue(0)
@maxValue(2)
param mcpMinReplicas int = 0

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
  tags: tags
}

var acrPullRoleId = loadYamlContent('../../content/config/workshop.yaml', '$.rbac_roles.acr_pull')

resource identityAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: acr
  name: guid(acr.id, identity.id, acrPullRoleId)
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
  }
}

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: last(split(logAnalyticsId, '/'))
}

resource cae 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

resource mcpApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: mcpAppName
  location: location
  tags: union(tags, { 'azd-service-name': 'mcp-activities' })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: cae.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 80
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: acr.properties.loginServer
          identity: identity.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'mcp-activities'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: mcpMinReplicas
        maxReplicas: 2
      }
    }
  }
  dependsOn: [
    identityAcrPull
  ]
}

output acrId string = acr.id
output acrName string = acr.name
output acrLoginServer string = acr.properties.loginServer
output identityId string = identity.id
output identityPrincipalId string = identity.properties.principalId
output identityClientId string = identity.properties.clientId
output environmentId string = cae.id
output environmentName string = cae.name
output mcpAppName string = mcpApp.name
output mcpAppFqdn string = mcpApp.properties.configuration.ingress.fqdn
