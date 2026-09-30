// Role assignments by role-definition ID (SPEC.md §8.3). Attendee assignments are NOT here — they are
// made by scripts/seed-attendees.sh so the attendee list never lives in the template.
param accountName string
param projectName string
param searchName string
param storageName string
param acrName string

@description('Object IDs of facilitator users (deployer included).')
param facilitatorPrincipalIds array
@allowed([
  'User'
  'ServicePrincipal'
  'Group'
])
param facilitatorPrincipalType string = 'User'

param projectPrincipalId string
param searchPrincipalId string

var r = loadYamlContent('../../content/config/workshop.yaml', '$.rbac_roles')
var roles = {
  foundryUser: r.foundry_user
  foundryProjectManager: r.foundry_project_manager
  cognitiveServicesUser: r.cognitive_services_user
  searchIndexDataReader: r.search_index_data_reader
  searchIndexDataContributor: r.search_index_data_contributor
  searchServiceContributor: r.search_service_contributor
  storageBlobDataReader: r.storage_blob_data_reader
  storageBlobDataContributor: r.storage_blob_data_contributor
  acrPull: r.acr_pull
  acrPush: r.acr_push
}

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: accountName

  resource project 'projects' existing = {
    name: projectName
  }
}

resource search 'Microsoft.Search/searchServices@2025-05-01' existing = {
  name: searchName
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageName
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

// --- Facilitators -------------------------------------------------------------------------------

resource facProjectManager 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for p in facilitatorPrincipalIds: {
    scope: account
    name: guid(account.id, p, roles.foundryProjectManager)
    properties: {
      principalId: p
      principalType: facilitatorPrincipalType
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.foundryProjectManager)
    }
  }
]

resource facFoundryUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for p in facilitatorPrincipalIds: {
    scope: account::project
    name: guid(account::project.id, p, roles.foundryUser)
    properties: {
      principalId: p
      principalType: facilitatorPrincipalType
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.foundryUser)
    }
  }
]

resource facSearchContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for p in facilitatorPrincipalIds: {
    scope: search
    name: guid(search.id, p, roles.searchServiceContributor)
    properties: {
      principalId: p
      principalType: facilitatorPrincipalType
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchServiceContributor)
    }
  }
]

resource facSearchData 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for p in facilitatorPrincipalIds: {
    scope: search
    name: guid(search.id, p, roles.searchIndexDataContributor)
    properties: {
      principalId: p
      principalType: facilitatorPrincipalType
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchIndexDataContributor)
    }
  }
]

resource facBlob 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for p in facilitatorPrincipalIds: {
    scope: storage
    name: guid(storage.id, p, roles.storageBlobDataContributor)
    properties: {
      principalId: p
      principalType: facilitatorPrincipalType
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.storageBlobDataContributor)
    }
  }
]

resource facAcrPush 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for p in facilitatorPrincipalIds: {
    scope: acr
    name: guid(acr.id, p, roles.acrPush)
    properties: {
      principalId: p
      principalType: facilitatorPrincipalType
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.acrPush)
    }
  }
]

// --- Foundry project managed identity -------------------------------------------------------------

resource projectSearchReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: search
  name: guid(search.id, projectPrincipalId, roles.searchIndexDataReader)
  properties: {
    principalId: projectPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchIndexDataReader)
  }
}

resource projectAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: acr
  name: guid(acr.id, projectPrincipalId, roles.acrPull)
  properties: {
    principalId: projectPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.acrPull)
  }
}

// Memory (preview): the memory store calls the chat + embedding deployments as the project identity.
// Without Foundry User on the account, memory search fails with 401 (ASSUMPTIONS.md 4.9).
resource projectFoundryUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: account
  name: guid(account.id, projectPrincipalId, roles.foundryUser)
  properties: {
    principalId: projectPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.foundryUser)
  }
}

// Evaluations: `evaluate(azure_ai_project=...)` uploads results through the project's storage connection
// as the project identity; without this it fails with ResourceMsiTokenDoesntHavePermissionsOnStorage.
resource projectBlobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(storage.id, projectPrincipalId, roles.storageBlobDataContributor)
  properties: {
    principalId: projectPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.storageBlobDataContributor)
  }
}

// --- Search managed identity (knowledge source ingestion + knowledge base model calls) --------------

resource searchCognitiveUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: account
  name: guid(account.id, searchPrincipalId, roles.cognitiveServicesUser)
  properties: {
    principalId: searchPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.cognitiveServicesUser)
  }
}

resource searchBlobReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(storage.id, searchPrincipalId, roles.storageBlobDataReader)
  properties: {
    principalId: searchPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.storageBlobDataReader)
  }
}
