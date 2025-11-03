# Azure Deployment Script for LeetCode Agent
param(
    [Parameter(Mandatory = $true)]
    [string]$ResourceGroupName,

    [Parameter(Mandatory = $false)]
    [string]$Location = "East US",

    [Parameter(Mandatory = $false)]
    [string]$Environment = "dev"
)

# Set error action preference
$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting Azure deployment for LeetCode Agent..." -ForegroundColor Green
Write-Host "Resource Group: $ResourceGroupName" -ForegroundColor Cyan
Write-Host "Location: $Location" -ForegroundColor Cyan
Write-Host "Environment: $Environment" -ForegroundColor Cyan

# Check if Azure CLI is installed
try {
    $azVersion = az --version 2>$null
    Write-Host "✅ Azure CLI is installed" -ForegroundColor Green
} catch {
    Write-Error "❌ Azure CLI is not installed. Please install it from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
}

# Login to Azure (if not already logged in)
$account = az account show 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "🔐 Please login to Azure..." -ForegroundColor Yellow
    az login
}

# Set subscription (optional - uncomment if needed)
# az account set --subscription "your-subscription-id"

# Create resource group if it doesn't exist
Write-Host "📁 Creating/checking resource group..." -ForegroundColor Yellow
az group create --name $ResourceGroupName --location $Location --tags Environment=$Environment Project="LeetCode Agent"

# Deploy Bicep template
Write-Host "🏗️  Deploying infrastructure with Bicep..." -ForegroundColor Yellow
$deploymentName = "leetcode-agent-deployment-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

az deployment group create `
    --resource-group $ResourceGroupName `
    --template-file "main.bicep" `
    --name $deploymentName `
    --parameters `
        resourceGroupName=$ResourceGroupName `
        location=$Location `
        environment=$Environment

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Infrastructure deployment completed successfully!" -ForegroundColor Green

    # Get deployment outputs
    Write-Host "📋 Retrieving deployment outputs..." -ForegroundColor Yellow
    $outputs = az deployment group show --resource-group $ResourceGroupName --name $deploymentName --query "properties.outputs" | ConvertFrom-Json

    # Get the actual keys using Azure CLI
    Write-Host "🔑 Retrieving service keys..." -ForegroundColor Yellow
    $cosmosEndpoint = $outputs.cosmosEndpoint.value
    $storageAccountName = $outputs.storageAccountName.value
    $openAiEndpoint = $outputs.openAiEndpoint.value
    $webAppName = $outputs.webAppName.value
    $webAppUrl = $outputs.webAppUrl.value

    # Calculate the unique string used in Bicep (same as uniqueString(resourceGroupName))
    $uniqueString = [System.BitConverter]::ToString([System.Security.Cryptography.SHA256]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($ResourceGroupName))).Replace("-", "").Substring(0, 13).ToLower()

    # Get resource names as defined in Bicep (with substring limits)
    $cosmosAccountName = "leetcosmos" + $uniqueString.Substring(0, 10)
    $openAiResourceName = "leetoai" + $uniqueString.Substring(0, 10)

    # Get CosmosDB key
    $cosmosKey = az cosmosdb keys list --name $cosmosAccountName --resource-group $ResourceGroupName --query "primaryMasterKey" -o tsv 2>$null

    # Get Storage account key
    $storageKey = az storage account keys list --account-name $storageAccountName --resource-group $ResourceGroupName --query "[0].value" -o tsv 2>$null

    # Get OpenAI key
    $openAiKey = az cognitiveservices account keys list --name $openAiResourceName --resource-group $ResourceGroupName --query "key1" -o tsv 2>$null

    Write-Host "`n🔑 Configuration Values:" -ForegroundColor Cyan
    Write-Host "CosmosDB Endpoint: $cosmosEndpoint" -ForegroundColor White
    Write-Host "Storage Account: $storageAccountName" -ForegroundColor White
    Write-Host "OpenAI Endpoint: $openAiEndpoint" -ForegroundColor White
    Write-Host "Web App URL: $webAppUrl" -ForegroundColor White

    # Create .env file for local development
    Write-Host "`n📝 Creating .env file for local development..." -ForegroundColor Yellow
    $envContent = @"
# Azure Configuration (from deployment)
AZURE_COSMOS_ENDPOINT=$cosmosEndpoint
AZURE_COSMOS_KEY=$cosmosKey
AZURE_STORAGE_ACCOUNT=$storageAccountName
AZURE_STORAGE_KEY=$storageKey

# OpenAI Configuration
OPENAI_API_BASE=$openAiEndpoint
OPENAI_API_KEY=$openAiKey
OPENAI_MODEL=gpt-4
OPENAI_DEPLOYMENT_NAME=gpt-4

# Application Configuration
DEBUG=true
MAX_CONCURRENT_REQUESTS=5
CACHE_TTL_SECONDS=3600

# LeetCode Configuration
LEETCODE_BASE_URL=https://leetcode.com
LEETCODE_API_URL=https://leetcode.com/api/problems/all/

# MCP Server Configuration (optional)
LEETCODE_MCP_SERVER=http://localhost:3333
"@

    $envContent | Out-File -FilePath "../.env" -Encoding UTF8 -Force
    Write-Host "✅ .env file created at ../.env" -ForegroundColor Green

    Write-Host "`n🎉 Deployment completed successfully!" -ForegroundColor Green
    Write-Host "📖 Next steps:" -ForegroundColor Cyan
    Write-Host "1. Review and update the .env file with any additional configuration" -ForegroundColor White
    Write-Host "2. Deploy the application code using: az webapp up --resource-group $ResourceGroupName --name leetcode-agent-app --src-path .." -ForegroundColor White
    Write-Host "3. Or use the GitHub Actions CI/CD pipeline" -ForegroundColor White

} else {
    Write-Error "❌ Infrastructure deployment failed!"
    exit 1
}
