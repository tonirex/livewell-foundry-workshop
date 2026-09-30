// Storage account for the knowledge blobs (Foundry IQ knowledge source reads the livewell-guides container).
// Network: Entra ID only (no shared keys, no anonymous blobs). networkDefaultAction 'Allow' (default) lets Lab 2
// publish evaluation runs from laptops; 'Deny' admits only the shared Search service (resource instance rule),
// trusted Azure services and, during scripts/build-kb.py uploads, the caller's IP. ASSUMPTIONS.md 4.4 / 4.15.
param location string
param tags object
param name string
param containerName string

@description('Resource ID of the Azure AI Search service whose indexer reads the knowledge container.')
param searchServiceId string

@description('Opt out of tenant "modify" policies that force publicNetworkAccess=Disabled (MCAPS: SecurityControl=Ignore). Empty = no tag.')
param policyOptOutTag object = {}

@description('Storage firewall default action: Allow (Entra-only public access; evaluation uploads work) or Deny.')
@allowed([
  'Allow'
  'Deny'
])
param networkDefaultAction string = 'Allow'

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: name
  location: location
  tags: union(tags, policyOptOutTag)
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: networkDefaultAction
      bypass: 'AzureServices'
      ipRules: []
      virtualNetworkRules: []
      resourceAccessRules: [
        {
          tenantId: tenant().tenantId
          resourceId: searchServiceId
        }
      ]
    }
  }

  resource blob 'blobServices' = {
    name: 'default'

    resource container 'containers' = {
      name: containerName
      properties: {
        publicAccess: 'None'
      }
    }
  }
}

output id string = storage.id
output name string = storage.name
output blobEndpoint string = storage.properties.primaryEndpoints.blob
output containerName string = storage::blob::container.name
