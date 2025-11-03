@description('The name of the resource group')
param resourceGroupName string = 'leetcode-agent-rg'

@description('Location for all resources.')
param location string = 'East US'

@description('Name of the Cosmos DB account')
param cosmosAccountName string = 'leetcosmos${substring(uniqueString(resourceGroupName), 0, 10)}'

@description('Name of the Storage account')
param storageAccountName string = 'leetstorage${substring(uniqueString(resourceGroupName), 0, 8)}'

@description('Name of the OpenAI resource')
param openAiResourceName string = 'leetoai${substring(uniqueString(resourceGroupName), 0, 10)}'

@description('Name of the Web App')
param webAppName string = 'leetcode-agent-app'

@description('Name of the Application Insights')
param appInsightsName string = 'leetcode-agent-insights'

@description('Environment name')
param environment string = 'dev'

var cosmosDatabaseName = 'leetcode-agent'
var storageContainerName = 'tutorials'
var tags = {
  Environment: environment
  Project: 'LeetCode Agent'
  ManagedBy: 'Bicep'
}

// Cosmos DB Account (Free Tier)
resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' = {
  name: cosmosAccountName
  location: location
  tags: tags
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
      maxStalenessPrefix: 100
      maxIntervalInSeconds: 5
    }
    enableAutomaticFailover: false
    enableMultipleWriteLocations: false
    enablePartitionMerge: false
    publicNetworkAccess: 'Enabled'
    enableBurstCapacity: false
    minimalTlsVersion: 'Tls12'
    ipRules: []
    backupPolicy: {
      type: 'Continuous'
    }
    // Enable free tier
    enableFreeTier: true
  }
}

// Cosmos DB Database
resource cosmosDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-04-15' = {
  parent: cosmosAccount
  name: cosmosDatabaseName
  properties: {
    resource: {
      id: cosmosDatabaseName
    }
  }
}

// Cosmos DB Containers
resource problemsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: cosmosDatabase
  name: 'problems'
  properties: {
    resource: {
      id: 'problems'
      partitionKey: {
        paths: [
          '/id'
        ]
        kind: 'Hash'
        version: 2
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/"_etag"/?'
          }
        ]
      }
    }
  }
}

resource patternsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: cosmosDatabase
  name: 'patterns'
  properties: {
    resource: {
      id: 'patterns'
      partitionKey: {
        paths: [
          '/name'
        ]
        kind: 'Hash'
        version: 2
      }
    }
  }
}

resource userProgressContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: cosmosDatabase
  name: 'user-progress'
  properties: {
    resource: {
      id: 'user-progress'
      partitionKey: {
        paths: [
          '/user_id'
        ]
        kind: 'Hash'
        version: 2
      }
    }
  }
}

// Storage Account
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    encryption: {
      services: {
        blob: {
          enabled: true
        }
        file: {
          enabled: true
        }
      }
      keySource: 'Microsoft.Storage'
    }
    accessTier: 'Hot'
  }
}

// Storage Blob Service
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

// Storage Container
resource storageContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: storageContainerName
  properties: {
    publicAccess: 'None'
  }
}

// OpenAI Resource
resource openAiResource 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: openAiResourceName
  location: location
  tags: tags
  sku: {
    name: 'S0'
  }
  kind: 'OpenAI'
  properties: {
    customSubDomainName: openAiResourceName
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

// Application Insights
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    Flow_Type: 'Bluefield'
    Request_Source: 'rest'
  }
}

// FREE TIER Web App (no App Service Plan needed)
resource webApp 'Microsoft.Web/sites@2022-09-01' = {
  name: webAppName
  location: location
  tags: tags
  properties: {
    // Free tier - no serverFarmId needed
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.10'
      appSettings: [
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'AZURE_COSMOS_ENDPOINT'
          value: cosmosAccount.properties.documentEndpoint
        }
        {
          name: 'AZURE_COSMOS_KEY'
          value: cosmosAccount.listKeys().primaryMasterKey
        }
        {
          name: 'AZURE_STORAGE_ACCOUNT'
          value: storageAccount.name
        }
        {
          name: 'AZURE_STORAGE_KEY'
          value: storageAccount.listKeys().keys[0].value
        }
        {
          name: 'AZURE_OPENAI_ENDPOINT'
          value: 'https://${openAiResourceName}.openai.azure.com/'
        }
        {
          name: 'AZURE_OPENAI_KEY'
          value: openAiResource.listKeys().key1
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
      ]
      cors: {
        allowedOrigins: [
          'https://portal.azure.com'
          'https://localhost:3000'
        ]
      }
    }
    // Free tier configuration
    sku: 'F1'
  }
}

// Outputs (secrets are retrieved via Azure CLI in deployment script)
output cosmosEndpoint string = cosmosAccount.properties.documentEndpoint
output storageAccountName string = storageAccount.name
output openAiEndpoint string = 'https://${openAiResourceName}.openai.azure.com/'
output webAppName string = webApp.name
output webAppUrl string = 'https://${webApp.name}.azurewebsites.net'

// Note: Keys are retrieved via 'az cosmosdb keys list' and 'az storage account keys list' in deployment script
