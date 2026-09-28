// Microsoft Fabric capacity (paid F SKU; trial capacities cannot host the ontology + data agent flow).
// Same resource group as everything else so azd down removes it. Pause outside sessions:
//   az fabric capacity suspend --resource-group <rg> --capacity-name <name>
param location string
param tags object
param name string

@description('Fabric capacity administrators: UPNs of member accounts in THIS tenant.')
param adminMembers array

@allowed([
  'F2'
  'F4'
  'F8'
])
param skuName string = 'F2'

resource capacity 'Microsoft.Fabric/capacities@2023-11-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: skuName
    tier: 'Fabric'
  }
  properties: {
    administration: {
      members: adminMembers
    }
  }
}

output id string = capacity.id
output name string = capacity.name
