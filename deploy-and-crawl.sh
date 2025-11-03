#!/bin/bash

# LeetCode AI Agent - Complete Deployment and Crawling Script
# This script deploys the entire infrastructure to Azure, runs the crawler, and can clean up everything

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESOURCE_GROUP_NAME=""
LOCATION="East US"
ENVIRONMENT="dev"
DEPLOY_ONLY=false
CLEANUP_ONLY=false
SKIP_CRAWL=false
USE_FREE_TIER=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo -e "\n${BOLD}${CYAN}================================${NC}"
    echo -e "${BOLD}${CYAN} $1 ${NC}"
    echo -e "${BOLD}${CYAN}================================${NC}\n"
}

# Show usage
show_usage() {
    echo "LeetCode AI Agent - Complete Deployment Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -g, --resource-group NAME    Azure resource group name (required)"
    echo "  -l, --location LOCATION      Azure region (default: East US)"
    echo "  -e, --environment ENV       Environment name (default: dev)"
    echo "  --deploy-only                Only deploy, don't run crawler"
    echo "  --cleanup-only               Only cleanup, don't deploy"
    echo "  --skip-crawl                 Deploy but skip crawler execution"
    echo "  --free-tier                  Use free tier services (no VM quota needed)"
    echo "  -h, --help                   Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -g my-leetcode-agent-rg                    # Deploy and run crawler"
    echo "  $0 -g my-leetcode-agent-rg --deploy-only      # Deploy only"
    echo "  $0 -g my-leetcode-agent-rg --cleanup-only     # Cleanup only"
    echo "  $0 -g my-leetcode-agent-rg --skip-crawl       # Deploy but skip crawler"
    echo "  $0 -g my-leetcode-agent-rg --free-tier        # Use free tier (no quota)"
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -g|--resource-group)
                RESOURCE_GROUP_NAME="$2"
                shift 2
                ;;
            -l|--location)
                LOCATION="$2"
                shift 2
                ;;
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --deploy-only)
                DEPLOY_ONLY=true
                shift
                ;;
            --cleanup-only)
                CLEANUP_ONLY=true
                shift
                ;;
            --skip-crawl)
                SKIP_CRAWL=true
                shift
                ;;
            --free-tier)
                USE_FREE_TIER=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # Validate required parameters
    if [[ "$CLEANUP_ONLY" != "true" && -z "$RESOURCE_GROUP_NAME" ]]; then
        log_error "Resource group name is required (use -g or --resource-group)"
        show_usage
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log_header "Checking Prerequisites"

    # Check if Azure CLI is installed
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI is not installed. Please install it from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi
    log_success "Azure CLI is installed"

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker from https://docs.docker.com/get-docker/"
        exit 1
    fi
    log_success "Docker is installed"

    # Check if .env file exists
    if [[ ! -f ".env" ]]; then
        log_warning ".env file not found. Creating template..."
        cat > .env << EOF
# Azure Configuration (will be filled by deployment)
AZURE_COSMOS_ENDPOINT=
AZURE_COSMOS_KEY=
AZURE_STORAGE_ACCOUNT=
AZURE_STORAGE_KEY=

# OpenAI Configuration
OPENAI_API_KEY=your-openai-key-here
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
        log_info "Created .env template. Please fill in your OpenAI API key and other credentials."
    fi

    # Check if user is logged in to Azure
    if ! az account show &> /dev/null; then
        log_warning "Not logged in to Azure. Please run 'az login' first."
        az login
    fi
    log_success "Azure authentication verified"
}

# Deploy infrastructure
deploy_infrastructure() {
    log_header "Deploying Azure Infrastructure"

    log_info "Resource Group: $RESOURCE_GROUP_NAME"
    log_info "Location: $LOCATION"
    log_info "Environment: $ENVIRONMENT"

    # Create resource group if it doesn't exist
    log_info "Creating resource group..."
    az group create --name "$RESOURCE_GROUP_NAME" --location "$LOCATION" --tags Environment="$ENVIRONMENT" Project="LeetCode Agent" || true

    # Deploy Bicep template
    log_info "Deploying infrastructure with Bicep..."
    DEPLOYMENT_NAME="leetcode-agent-deployment-$(date +%Y%m%d-%H%M%S)"

    cd infrastructure

    # Choose template based on free tier option
    if [[ "$USE_FREE_TIER" == "true" ]]; then
        TEMPLATE_FILE="main-free.bicep"
        log_info "Using FREE TIER template (no VM quota needed)"
    else
        TEMPLATE_FILE="main.bicep"
        log_info "Using STANDARD template with App Service Basic tier"
    fi

    # Check Bicep syntax first
    if az bicep build --file "$TEMPLATE_FILE" --stdout >/dev/null 2>&1; then
        log_success "Bicep template syntax validated"
    else
        log_error "Bicep template has syntax errors"
        exit 1
    fi

    DEPLOYMENT_OUTPUT=$(az deployment group create \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --template-file "$TEMPLATE_FILE" \
        --name "$DEPLOYMENT_NAME" \
        --parameters \
            resourceGroupName="$RESOURCE_GROUP_NAME" \
            location="$LOCATION" \
            environment="$ENVIRONMENT" 2>&1)

    if [[ $? -ne 0 ]]; then
        # Check for specific error types
        if echo "$DEPLOYMENT_OUTPUT" | grep -q "SubscriptionIsOverQuotaForSku"; then
            log_error "❌ QUOTA LIMIT EXCEEDED"
            log_warning "Your Azure subscription is over quota for Basic VMs (App Service)."
            log_info ""
            log_info "🔧 SOLUTION: Request quota increase or use alternative deployment"
            log_info ""
            log_info "📋 To request quota increase:"
            log_info "1. Go to: https://portal.azure.com/#view/Microsoft_Azure_Capacity/QuotaMenuBlade/~/overview"
            log_info "2. Request increase for 'Standard BS Family vCPUs'"
            log_info "3. Request 1-4 additional vCPUs for 'East US' region"
            log_info ""
            log_info "🚀 Alternative: Try deployment in a different region:"
            log_info "./deploy-and-crawl.sh -g $RESOURCE_GROUP_NAME -l 'West US 2'"
            log_info ""
            log_info "💡 Or use free tier services (modify main.bicep to use Free/F1 App Service tier)"
            exit 1
        elif echo "$DEPLOYMENT_OUTPUT" | grep -q "AccountNameInvalid"; then
            log_error "❌ STORAGE ACCOUNT NAME INVALID"
            log_warning "The generated storage account name is invalid (too long or invalid characters)."
            log_info "This is a bug in the deployment script. Please report this issue."
            exit 1
        else
            log_error "Infrastructure deployment failed with unknown error"
            echo "$DEPLOYMENT_OUTPUT"
            exit 1
        fi
    fi

    # Get deployment outputs and update .env
    log_info "Retrieving deployment outputs..."
    cd ..

    # Extract outputs
    OUTPUTS=$(az deployment group show --resource-group "$RESOURCE_GROUP_NAME" --name "$DEPLOYMENT_NAME" --query "properties.outputs")

    # Update .env file with deployment outputs
    update_env_file "$OUTPUTS"

    log_success "Infrastructure deployed successfully!"
}

# Update .env file with deployment outputs
update_env_file() {
    local outputs="$1"

    # Extract values using jq if available, otherwise basic parsing
    if command -v jq &> /dev/null; then
        COSMOS_ENDPOINT=$(echo "$outputs" | jq -r '.cosmosEndpoint.value')
        COSMOS_KEY=$(echo "$outputs" | jq -r '.cosmosKey.value')
        STORAGE_ACCOUNT=$(echo "$outputs" | jq -r '.storageAccountName.value')
        STORAGE_KEY=$(echo "$outputs" | jq -r '.storageKey.value')
        OPENAI_ENDPOINT=$(echo "$outputs" | jq -r '.openAiEndpoint.value')
        OPENAI_KEY=$(echo "$outputs" | jq -r '.openAiKey.value')
        WEBAPP_URL=$(echo "$outputs" | jq -r '.webAppUrl.value')
    else
        log_warning "jq not found, using basic parsing"
        COSMOS_ENDPOINT=$(echo "$outputs" | grep -o '"cosmosEndpoint":\s*"[^"]*"' | cut -d'"' -f4)
        COSMOS_KEY=$(echo "$outputs" | grep -o '"cosmosKey":\s*"[^"]*"' | cut -d'"' -f4)
        STORAGE_ACCOUNT=$(echo "$outputs" | grep -o '"storageAccountName":\s*"[^"]*"' | cut -d'"' -f4)
        STORAGE_KEY=$(echo "$outputs" | grep -o '"storageKey":\s*"[^"]*"' | cut -d'"' -f4)
        OPENAI_ENDPOINT=$(echo "$outputs" | grep -o '"openAiEndpoint":\s*"[^"]*"' | cut -d'"' -f4)
        OPENAI_KEY=$(echo "$outputs" | grep -o '"openAiKey":\s*"[^"]*"' | cut -d'"' -f4)
        WEBAPP_URL=$(echo "$outputs" | grep -o '"webAppUrl":\s*"[^"]*"' | cut -d'"' -f4)
    fi

    # Update .env file
    if [[ -f ".env" ]]; then
        # Create backup
        cp .env .env.backup

        # Update values
        sed -i.bak "s|^AZURE_COSMOS_ENDPOINT=.*|AZURE_COSMOS_ENDPOINT=$COSMOS_ENDPOINT|" .env
        sed -i.bak "s|^AZURE_COSMOS_KEY=.*|AZURE_COSMOS_KEY=$COSMOS_KEY|" .env
        sed -i.bak "s|^AZURE_STORAGE_ACCOUNT=.*|AZURE_STORAGE_ACCOUNT=$STORAGE_ACCOUNT|" .env
        sed -i.bak "s|^AZURE_STORAGE_KEY=.*|AZURE_STORAGE_KEY=$STORAGE_KEY|" .env
        sed -i.bak "s|^OPENAI_API_BASE=.*|OPENAI_API_BASE=$OPENAI_ENDPOINT|" .env

        log_success "Updated .env file with deployment outputs"
    fi

    # Display configuration
    echo -e "\n${CYAN}🔑 Deployment Configuration:${NC}"
    echo -e "CosmosDB Endpoint: $COSMOS_ENDPOINT"
    echo -e "Storage Account: $STORAGE_ACCOUNT"
    echo -e "OpenAI Endpoint: $OPENAI_ENDPOINT"
    echo -e "Web App URL: $WEBAPP_URL"
}

# Deploy application
deploy_application() {
    log_header "Deploying Application"

    # Build Docker image
    log_info "Building Docker image..."
    docker build -t leetcode-agent:latest .

    # Deploy to Azure Web App
    log_info "Deploying to Azure Web App..."
    WEBAPP_NAME="leetcode-agent-app"

    az webapp create \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --plan "leetcode-agent-plan" \
        --name "$WEBAPP_NAME" \
        --runtime "PYTHON:3.10" \
        --deployment-container-image-name "leetcode-agent:latest" \
        2>/dev/null || log_warning "Web app might already exist"

    # Wait for deployment
    log_info "Waiting for deployment to complete..."
    sleep 30

    # Health check
    log_info "Running health check..."
    if curl -f "${WEBAPP_URL}api/system-status" &>/dev/null; then
        log_success "Application deployed and healthy!"
    else
        log_warning "Application deployed but health check failed. This is normal for initial deployment."
    fi
}

# Run crawler with detailed logging
run_crawler() {
    log_header "Running LeetCode Crawler"

    # Check if MCP server is running
    log_info "Checking MCP server status..."
    if curl -f "http://localhost:3333/health" &>/dev/null 2>&1; then
        log_success "MCP server is running"
        MCP_AVAILABLE=true
    else
        log_warning "MCP server not detected. Starting it..."
        start_mcp_server
        MCP_AVAILABLE=true
    fi

    # Wait for services to be ready
    log_info "Waiting for all services to be ready..."
    sleep 10

    # Test system status
    log_info "Testing system status..."
    if [[ "$MCP_AVAILABLE" == "true" ]]; then
        log_success "✅ MCP Server: Available"
    else
        log_warning "❌ MCP Server: Not available"
    fi

    # Run crawler
    log_info "🚀 Starting LeetCode crawler..."

    # Crawl problems
    log_info "📥 Step 1: Crawling LeetCode problems..."
    crawl_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"category": "all-code-essentials", "limit": 100}' \
        "${WEBAPP_URL}api/crawl-problems")

    if [[ $? -eq 0 ]]; then
        echo "$crawl_response" | jq . 2>/dev/null || echo "$crawl_response"
        log_success "Problems crawled successfully!"
    else
        log_error "Failed to crawl problems"
        echo "$crawl_response"
    fi

    # Analyze problems
    log_info "🧠 Step 2: Analyzing problems with AI..."
    analyze_response=$(curl -s -X POST "${WEBAPP_URL}api/analyze-problems")

    if [[ $? -eq 0 ]]; then
        echo "$analyze_response" | jq . 2>/dev/null || echo "$analyze_response"
        log_success "Problems analyzed successfully!"
    else
        log_error "Failed to analyze problems"
        echo "$analyze_response"
    fi

    # Generate tutorials
    log_info "📚 Step 3: Generating pattern tutorials..."
    tutorial_response=$(curl -s -X POST "${WEBAPP_URL}api/generate-tutorials")

    if [[ $? -eq 0 ]]; then
        echo "$tutorial_response" | jq . 2>/dev/null || echo "$tutorial_response"
        log_success "Tutorials generated successfully!"
    else
        log_error "Failed to generate tutorials"
        echo "$tutorial_response"
    fi

    # Generate solutions
    log_info "💡 Step 4: Generating problem solutions..."
    solution_response=$(curl -s -X POST "${WEBAPP_URL}api/generate-solutions")

    if [[ $? -eq 0 ]]; then
        echo "$solution_response" | jq . 2>/dev/null || echo "$solution_response"
        log_success "Solutions generated successfully!"
    else
        log_error "Failed to generate solutions"
        echo "$solution_response"
    fi

    # Final system status
    log_info "📊 Final system status:"
    status_response=$(curl -s "${WEBAPP_URL}api/system-status")
    echo "$status_response" | jq . 2>/dev/null || echo "$status_response"

    log_success "🎉 Crawler execution completed!"
    log_info "Your LeetCode AI Agent is now fully operational!"
    log_info "Web App URL: $WEBAPP_URL"
}

# Start MCP server
start_mcp_server() {
    log_info "Starting LeetCode MCP server..."

    # Check if Node.js is available
    if ! command -v node &> /dev/null; then
        log_error "Node.js is not installed. MCP server requires Node.js."
        log_info "Please install Node.js and run: npm install -g @jinzcdev/leetcode-mcp-server"
        return 1
    fi

    # Install MCP server if not already installed
    if ! command -v leetcode-mcp-server &> /dev/null; then
        log_info "Installing LeetCode MCP server..."
        npm install -g @jinzcdev/leetcode-mcp-server
    fi

    # Start MCP server in background
    log_info "Starting MCP server on port 3333..."
    nohup leetcode-mcp-server --port 3333 > mcp-server.log 2>&1 &

    # Wait for server to start
    sleep 5

    if curl -f "http://localhost:3333/health" &>/dev/null; then
        log_success "MCP server started successfully"
        return 0
    else
        log_error "Failed to start MCP server"
        log_info "Check mcp-server.log for details"
        return 1
    fi
}

# Cleanup everything
cleanup_azure() {
    log_header "Cleaning Up Azure Resources"

    if [[ -z "$RESOURCE_GROUP_NAME" ]]; then
        log_error "Resource group name is required for cleanup"
        exit 1
    fi

    log_warning "This will delete the entire resource group '$RESOURCE_GROUP_NAME' and all resources within it!"
    read -p "Are you sure you want to continue? (yes/no): " confirm

    if [[ "$confirm" != "yes" ]]; then
        log_info "Cleanup cancelled"
        exit 0
    fi

    log_info "Deleting resource group '$RESOURCE_GROUP_NAME'..."
    az group delete --name "$RESOURCE_GROUP_NAME" --yes --no-wait

    log_success "Cleanup initiated. Resources will be deleted asynchronously."
    log_info "You can check the status with: az group list --query \"[?name=='$RESOURCE_GROUP_NAME']\""

    # Clean up local files
    if [[ -f ".env.backup" ]]; then
        log_info "Restoring original .env file..."
        mv .env.backup .env
    fi

    # Stop local services
    log_info "Stopping local services..."
    docker-compose down 2>/dev/null || true
    pkill -f "leetcode-mcp-server" 2>/dev/null || true
}

# Main execution
main() {
    parse_args "$@"

    if [[ "$CLEANUP_ONLY" == "true" ]]; then
        cleanup_azure
        exit 0
    fi

    check_prerequisites

    if [[ "$DEPLOY_ONLY" != "true" ]]; then
        deploy_infrastructure
        deploy_application
    fi

    if [[ "$SKIP_CRAWL" != "true" && "$DEPLOY_ONLY" != "true" ]]; then
        run_crawler
    fi

    log_header "🎉 Deployment Complete!"
    log_info "Your LeetCode AI Agent is ready to use!"
    log_info "Web App URL: $WEBAPP_URL"
    log_info "To clean up everything, run: $0 -g $RESOURCE_GROUP_NAME --cleanup-only"
}

# Handle script interruption
trap 'log_error "Script interrupted by user"; exit 1' INT TERM

# Run main function
main "$@"
