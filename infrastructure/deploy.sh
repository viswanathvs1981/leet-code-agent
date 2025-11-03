#!/bin/bash

# Azure Deployment Script for LeetCode Agent (Bash)
set -e

# Default values
RESOURCE_GROUP_NAME=""
LOCATION="East US"
ENVIRONMENT="dev"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --resource-group|-rg)
      RESOURCE_GROUP_NAME="$2"
      shift 2
      ;;
    --location|-l)
      LOCATION="$2"
      shift 2
      ;;
    --environment|-e)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --help|-h)
      echo "Azure Deployment Script for LeetCode Agent"
      echo ""
      echo "Usage: $0 --resource-group <name> [options]"
      echo ""
      echo "Required:"
      echo "  --resource-group, -rg    Name of the Azure resource group"
      echo ""
      echo "Optional:"
      echo "  --location, -l           Azure region (default: East US)"
      echo "  --environment, -e        Environment name (default: dev)"
      echo "  --help, -h              Show this help message"
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Validate required parameters
if [ -z "$RESOURCE_GROUP_NAME" ]; then
  echo -e "${RED}Error: Resource group name is required${NC}"
  echo "Use --help for usage information"
  exit 1
fi

echo -e "${GREEN}🚀 Starting Azure deployment for LeetCode Agent...${NC}"
echo -e "${CYAN}Resource Group: $RESOURCE_GROUP_NAME${NC}"
echo -e "${CYAN}Location: $LOCATION${NC}"
echo -e "${CYAN}Environment: $ENVIRONMENT${NC}"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}❌ Azure CLI is not installed. Please install it from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Azure CLI is installed${NC}"

# Login to Azure (if not already logged in)
if ! az account show &> /dev/null; then
    echo -e "${YELLOW}🔐 Please login to Azure...${NC}"
    az login
fi

# Set subscription (optional - uncomment if needed)
# az account set --subscription "your-subscription-id"

# Create resource group if it doesn't exist
echo -e "${YELLOW}📁 Creating/checking resource group...${NC}"
az group create --name "$RESOURCE_GROUP_NAME" --location "$LOCATION" --tags Environment="$ENVIRONMENT" Project="LeetCode Agent"

# Deploy Bicep template
echo -e "${YELLOW}🏗️  Deploying infrastructure with Bicep...${NC}"
DEPLOYMENT_NAME="leetcode-agent-deployment-$(date +%Y%m%d-%H%M%S)"

az deployment group create \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --template-file "main.bicep" \
    --name "$DEPLOYMENT_NAME" \
    --parameters \
        resourceGroupName="$RESOURCE_GROUP_NAME" \
        location="$LOCATION" \
        environment="$ENVIRONMENT"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Infrastructure deployment completed successfully!${NC}"

    # Get deployment outputs
    echo -e "${YELLOW}📋 Retrieving deployment outputs...${NC}"
    OUTPUTS=$(az deployment group show --resource-group "$RESOURCE_GROUP_NAME" --name "$DEPLOYMENT_NAME" --query "properties.outputs" -o json)

    # Parse basic outputs
    if command -v jq &> /dev/null; then
        COSMOS_ENDPOINT=$(echo "$OUTPUTS" | jq -r '.cosmosEndpoint.value')
        STORAGE_ACCOUNT=$(echo "$OUTPUTS" | jq -r '.storageAccountName.value')
        OPENAI_ENDPOINT=$(echo "$OUTPUTS" | jq -r '.openAiEndpoint.value')
        WEBAPP_NAME=$(echo "$OUTPUTS" | jq -r '.webAppName.value')
        WEBAPP_URL=$(echo "$OUTPUTS" | jq -r '.webAppUrl.value')
    else
        echo -e "${YELLOW}⚠️  jq not found, using basic parsing. Install jq for better output formatting.${NC}"
        COSMOS_ENDPOINT=$(echo "$OUTPUTS" | grep -o '"cosmosEndpoint":\s*"[^"]*"' | cut -d'"' -f4)
        STORAGE_ACCOUNT=$(echo "$OUTPUTS" | grep -o '"storageAccountName":\s*"[^"]*"' | cut -d'"' -f4)
        OPENAI_ENDPOINT=$(echo "$OUTPUTS" | grep -o '"openAiEndpoint":\s*"[^"]*"' | cut -d'"' -f4)
        WEBAPP_NAME=$(echo "$OUTPUTS" | grep -o '"webAppName":\s*"[^"]*"' | cut -d'"' -f4)
        WEBAPP_URL=$(echo "$OUTPUTS" | grep -o '"webAppUrl":\s*"[^"]*"' | cut -d'"' -f4)
    fi

    # Calculate unique string (same as Bicep's uniqueString function)
    UNIQUE_STRING=$(echo -n "$RESOURCE_GROUP_NAME" | sha256sum | cut -c1-13)

    # Get resource names as defined in Bicep (with substring limits)
    COSMOS_ACCOUNT_NAME="leetcosmos${UNIQUE_STRING:0:10}"
    OPENAI_RESOURCE_NAME="leetoai${UNIQUE_STRING:0:10}"

    # Get actual keys using Azure CLI
    log_info "Retrieving service keys..."
    COSMOS_KEY=$(az cosmosdb keys list --name "$COSMOS_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP_NAME" --query "primaryMasterKey" -o tsv 2>/dev/null)
    STORAGE_KEY=$(az storage account keys list --account-name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP_NAME" --query "[0].value" -o tsv 2>/dev/null)
    OPENAI_KEY=$(az cognitiveservices account keys list --name "$OPENAI_RESOURCE_NAME" --resource-group "$RESOURCE_GROUP_NAME" --query "key1" -o tsv 2>/dev/null)

    # Display outputs
    echo -e "\n${CYAN}🔑 Configuration Values:${NC}"
    echo -e "CosmosDB Endpoint: $COSMOS_ENDPOINT"
    echo -e "Storage Account: $STORAGE_ACCOUNT"
    echo -e "OpenAI Endpoint: $OPENAI_ENDPOINT"
    echo -e "Web App URL: $WEBAPP_URL"

    # Create .env file for local development
    echo -e "\n${YELLOW}📝 Creating .env file for local development...${NC}"
    cat > ../.env << EOF
# Azure Configuration (from deployment)
AZURE_COSMOS_ENDPOINT=$COSMOS_ENDPOINT
AZURE_COSMOS_KEY=$COSMOS_KEY
AZURE_STORAGE_ACCOUNT=$STORAGE_ACCOUNT
AZURE_STORAGE_KEY=$STORAGE_KEY

# OpenAI Configuration
OPENAI_API_BASE=$OPENAI_ENDPOINT
OPENAI_API_KEY=$OPENAI_KEY
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
EOF

    echo -e "${GREEN}✅ .env file created at ../.env${NC}"

    echo -e "\n${GREEN}🎉 Deployment completed successfully!${NC}"
    echo -e "${CYAN}📖 Next steps:${NC}"
    echo -e "1. Review and update the .env file with any additional configuration"
    echo -e "2. Deploy the application code using: az webapp up --resource-group $RESOURCE_GROUP_NAME --name leetcode-agent-app --src-path .."
    echo -e "3. Or use the GitHub Actions CI/CD pipeline"

else
    echo -e "${RED}❌ Infrastructure deployment failed!${NC}"
    exit 1
fi
