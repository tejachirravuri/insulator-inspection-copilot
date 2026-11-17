// Azure infrastructure for the Insulator Inspection Copilot.
//
//   Container Registry (Basic, private)  <- image incl. YOLO weights, built with `az acr build`
//   PostgreSQL Flexible Server (B1ms)    <- documents, vectors (pgvector), inspections
//   Container Apps environment + app     <- FastAPI service, scales to zero when idle
//
// The app pulls its image with a user-assigned managed identity (AcrPull role), so no registry
// password exists. Secrets (database URL, Claude API key, access code) are Container Apps
// secrets, injected as environment variables, never baked into the image.

@description('Azure region. PostgreSQL Flexible Server is restricted for student subscriptions in Germany West Central, hence Sweden Central.')
param location string = 'swedencentral'

@description('Region for PostgreSQL. Student subscriptions cannot create Burstable servers in every region (Germany West Central and Sweden Central were refused), so it can differ.')
param postgresLocation string = location

@description('Name of the PostgreSQL server (empty = generated).')
param postgresName string = ''

@description('Short prefix for resource names (lowercase letters and digits).')
param prefix string = 'inspcopilot'

@description('Container image to run. The first deployment uses a public placeholder.')
param image string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('Port the container listens on (8000 for our image, 80 for the placeholder).')
param targetPort int = 80

@secure()
@description('PostgreSQL administrator password (letters and digits only).')
param postgresPassword string

@secure()
@description('Claude API key.')
param anthropicApiKey string

@secure()
@description('Access code visitors need to use the demo.')
param accessCode string

@description('Public IP allowed to reach PostgreSQL directly (for loading data). Empty = none.')
param clientIp string = ''

var suffix = uniqueString(resourceGroup().id)
var postgresUser = 'copilotadmin'
var databaseName = 'copilot'
var pgName = empty(postgresName) ? '${prefix}-db-${suffix}' : postgresName

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: '${prefix}${suffix}'
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-pull'
  location: location
}

// AcrPull built-in role: the identity may pull images, nothing else.
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, identity.id, acrPullRoleId)
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: pgName
  location: postgresLocation
  sku: { name: 'Standard_B1ms', tier: 'Burstable' }
  properties: {
    version: '16'
    administratorLogin: postgresUser
    administratorLoginPassword: postgresPassword
    storage: { storageSizeGB: 32 }
    backup: { backupRetentionDays: 7, geoRedundantBackup: 'Disabled' }
    highAvailability: { mode: 'Disabled' }
    // Public endpoint, but only reachable through the firewall rules below, and only with SSL.
    network: { publicNetworkAccess: 'Enabled' }
  }
}

// pgvector must be allow-listed on Azure before CREATE EXTENSION works.
resource extensions 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2024-08-01' = {
  parent: postgres
  name: 'azure.extensions'
  properties: { value: 'VECTOR', source: 'user-override' }
}

// The server accepts one change at a time, so the child resources are chained with dependsOn
// (in parallel Azure answers "server is busy processing another operation").
resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgres
  name: databaseName
  properties: { charset: 'UTF8', collation: 'en_US.utf8' }
  dependsOn: [extensions]
}

// 0.0.0.0 is Azure's convention for "allow connections from Azure services".
resource allowAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = {
  parent: postgres
  name: 'AllowAzureServices'
  properties: { startIpAddress: '0.0.0.0', endIpAddress: '0.0.0.0' }
  dependsOn: [database]
}

resource allowClient 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = if (!empty(clientIp)) {
  parent: postgres
  name: 'AllowDeveloperIp'
  properties: { startIpAddress: clientIp, endIpAddress: clientIp }
  dependsOn: [allowAzure]
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${prefix}-env'
  location: location
  properties: {} // no Log Analytics workspace: saves cost; live log streaming still works
}

var databaseUrl = 'postgresql+asyncpg://${postgresUser}:${postgresPassword}@${postgres.properties.fullyQualifiedDomainName}:5432/${databaseName}?ssl=require'

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${prefix}-app'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identity.id}': {} }
  }
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      ingress: { external: true, targetPort: targetPort, transport: 'auto' }
      registries: [{ server: registry.properties.loginServer, identity: identity.id }]
      secrets: [
        { name: 'database-url', value: databaseUrl }
        { name: 'anthropic-api-key', value: anthropicApiKey }
        { name: 'access-code', value: accessCode }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: image
          resources: { cpu: json('1.0'), memory: '2Gi' }
          env: [
            { name: 'DATABASE_URL', secretRef: 'database-url' }
            { name: 'ANTHROPIC_API_KEY', secretRef: 'anthropic-api-key' }
            { name: 'ACCESS_CODE', secretRef: 'access-code' }
            { name: 'DAILY_LLM_BUDGET_USD', value: '1.0' }
          ]
        }
      ]
      scale: { minReplicas: 0, maxReplicas: 1 } // scale to zero: no compute cost when idle
    }
  }
  dependsOn: [acrPull, database, extensions, allowAzure]
}

output registryName string = registry.name
output registryLoginServer string = registry.properties.loginServer
output postgresHost string = postgres.properties.fullyQualifiedDomainName
output appUrl string = 'https://${app.properties.configuration.ingress.fqdn}'
