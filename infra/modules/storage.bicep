// Storage account for the knowledge blobs (Foundry IQ knowledge source reads the livewell-guides container).
param location string
param tags object
param name string
param containerName string

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: name
  location: location
  tags: tags
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
      defaultAction: 'Allow'
      bypass: 'AzureServices'
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
