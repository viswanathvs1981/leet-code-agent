#!/bin/bash

# Azure Quota Request Script for LeetCode Agent
# This script helps request the necessary quota increases for deployment

set -e

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

# Check Azure CLI and login
check_azure_setup() {
    log_header "Checking Azure Setup"

    if ! command -v az &> /dev/null; then
        log_error "Azure CLI is not installed. Please install it from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi
    log_success "Azure CLI is installed"

    # Check if logged in
    if ! az account show &> /dev/null; then
        log_warning "Not logged in to Azure"
        log_info "Please run: az login"
        az login
    fi

    # Get current subscription
    SUBSCRIPTION_ID=$(az account show --query id -o tsv)
    SUBSCRIPTION_NAME=$(az account show --query name -o tsv)
    log_success "Using subscription: $SUBSCRIPTION_NAME ($SUBSCRIPTION_ID)"
}

# Check current quotas
check_current_quotas() {
    log_header "Checking Current Quotas"

    LOCATION="eastus"

    log_info "Checking VM quotas in $LOCATION..."

    # Check Basic VMs quota (used by App Service)
    BASIC_VM_QUOTA=$(az vm list-usage --location "$LOCATION" --query "[?name.value=='standardBSFamily'].{current:currentValue, limit:limit, available:limit-currentValue}" -o table 2>/dev/null || echo "Unable to check quota")

    if [[ "$BASIC_VM_QUOTA" == "Unable to check quota" ]]; then
        log_warning "Unable to check VM quotas automatically"
        log_info "You can check quotas manually at: https://portal.azure.com/#view/Microsoft_Azure_Capacity/QuotaMenuBlade/~/overview"
    else
        echo "$BASIC_VM_QUOTA"
    fi

    log_info "Checking other relevant quotas..."

    # Check total regional vCPUs
    VCPU_QUOTA=$(az vm list-usage --location "$LOCATION" --query "[?name.value=='cores'].{current:currentValue, limit:limit, available:limit-currentValue}" -o table 2>/dev/null || echo "Unable to check vCPU quota")

    if [[ "$VCPU_QUOTA" != "Unable to check vCPU quota" ]]; then
        echo "$VCPU_QUOTA"
    fi
}

# Generate quota request
generate_quota_request() {
    log_header "Generating Quota Request Information"

    cat << 'EOF'
🔧 AZURE QUOTA REQUEST TEMPLATE
================================

To request quota increases for your Azure subscription, follow these steps:

1. Go to: https://portal.azure.com/#view/Microsoft_Azure_Capacity/QuotaMenuBlade/~/overview

2. In the Azure portal, search for "Quotas" or navigate to:
   Home > Subscriptions > [Your Subscription] > Usage + quotas

3. Look for these quota types that need to be increased:
   - Standard BS Family vCPUs (Basic VMs) - Request: 1 additional
   - Total Regional vCPUs - Request: 1-4 additional (if needed)

4. For each quota type:
   - Click on the quota name
   - Click "Request quota increase"
   - Fill out the request form with these details:

REQUEST FORM DETAILS:
=====================

Quota Type: Standard BS Family vCPUs (or Total Regional vCPUs)
New Limit Requested: [Current Limit + 1-4]
Reason for Request: Deploying a web application using Azure App Service with Basic tier
Deployment Location: East US
Expected Usage: Low - development/testing of AI-powered application
Business Justification: Building a LeetCode problem analysis platform for educational purposes

SUPPORTING INFORMATION:
- Application Type: Web Application (Flask/Python)
- Expected Users: 1-10 concurrent users
- Hosting: Azure App Service Basic tier (1 B1 instance)
- Database: Azure CosmosDB (serverless/free tier available)
- Storage: Azure Blob Storage (minimal usage)
- AI Services: Azure OpenAI (pay-as-you-go)

TIMELINE:
- Need quota increase within 1-2 business days
- Will scale down/remove resources after testing

CONTACT INFORMATION:
- Use your current Azure account contact details

ALTERNATIVE SOLUTIONS:
======================

If quota increase is not immediately available, consider these alternatives:

1. **Use Free Tier Services:**
   - Azure CosmosDB has a free tier (first 400 RU/s and 5GB storage)
   - Azure Functions (Consumption plan) instead of App Service
   - Use existing Azure OpenAI quota if available

2. **Deploy to Different Region:**
   - Try "West US 2", "Central US", or "North Europe"
   - Different regions may have different quota availability

3. **Use Azure Free Account Benefits:**
   - If you have an Azure free account, you get:
     - 750 hours of B1 App Service instances per month
     - Free CosmosDB up to limits
     - Free Blob Storage up to 5GB

4. **Scale Down Temporarily:**
   - Use Free/F1 App Service tier for initial testing
   - Upgrade to Basic tier only when needed

MONITORING RESOURCE USAGE:
==========================

After deployment, monitor your usage at:
https://portal.azure.com/#view/Microsoft_Azure_Billing/ModernBillingMenuBlade/~/overview

Set up alerts for:
- App Service compute hours
- CosmosDB RU consumption
- Storage transactions

This will help you understand actual usage patterns and optimize costs.
EOF
}

# Provide alternative deployment options
alternative_deployments() {
    log_header "Alternative Deployment Options"

    cat << 'EOF'
🚀 ALTERNATIVE DEPLOYMENT STRATEGIES
=====================================

If quota increase is delayed, try these alternatives:

1. FREE TIER DEPLOYMENT
=======================
Use Azure free tier services:

# Modify the Bicep template to use free tiers:
# - App Service: Change to Free/F1 tier
# - CosmosDB: Use free tier (400 RU/s, 5GB)
# - Storage: Free up to 5GB

2. AZURE FUNCTIONS (Consumption Plan)
=====================================
Deploy as serverless functions instead of App Service:

# Benefits:
# - No VM quota issues
# - Pay-per-execution
# - Automatic scaling
# - Free tier: 1M requests/month

3. DIFFERENT AZURE REGION
=========================
Try regions with more available quota:

# Suggested regions to try:
# - West US 2
# - Central US
# - North Europe
# - UK South
# - Australia East

# Update your deployment command:
./deploy-and-crawl.sh -g my-leetcode-agent-rg -l "West US 2"

4. LOCAL DEVELOPMENT ONLY
=========================
Run everything locally without Azure deployment:

# Start MCP server locally:
npm install -g @jinzcdev/leetcode-mcp-server
export LEETCODE_SESSION="your_session_cookie"
leetcode-mcp-server --port 3333

# Run the application locally:
python app.py

# Use local databases (SQLite, local files) instead of Azure services

5. DOCKER COMPOSE ONLY
======================
Run everything in local containers:

docker-compose up -d

# This runs:
# - Flask app on port 8000
# - MCP server on port 3333
# - Local data persistence

6. AZURE STATIC WEB APP + FUNCTIONS
===================================
Deploy frontend as static site, backend as functions:

# Benefits:
# - No App Service VM quota
# - Functions have generous free tier
# - Static web apps are free

WOULD YOU LIKE TO TRY ANY OF THESE ALTERNATIVES?
================================================

Choose an option:
1. Try different Azure region
2. Use free tier services (modify Bicep template)
3. Deploy locally only
4. Use Docker Compose only
5. Continue waiting for quota approval

Let me know which option you'd prefer, and I can help you implement it!
EOF
}

# Main execution
main() {
    log_header "🔧 Azure Quota Request Helper"
    echo -e "${CYAN}This tool helps you request Azure quota increases needed for LeetCode Agent deployment${NC}"

    check_azure_setup
    check_current_quotas
    generate_quota_request
    alternative_deployments

    log_header "📞 Next Steps"

    cat << 'EOF'
🎯 IMMEDIATE ACTIONS:
===================

1. **Request Quota Increase:**
   - Go to: https://portal.azure.com/#view/Microsoft_Azure_Capacity/QuotaMenuBlade/~/overview
   - Request increase for "Standard BS Family vCPUs"
   - Request 1-4 additional vCPUs

2. **Monitor Request Status:**
   - Check email for approval notifications
   - Quota increases are typically approved within 1-2 business days

3. **Alternative Deployment:**
   - Try a different Azure region with available quota
   - Use free tier services temporarily

4. **Contact Azure Support (if needed):**
   - For urgent requests, create a support ticket
   - Use "Technical Issue" > "Service and subscription limits"

WOULD YOU LIKE ME TO HELP WITH ANY OF THESE OPTIONS?
==================================================

Choose what you'd like to do next:
- A: Help modify Bicep template for free tier services
- B: Try deployment in a different region
- C: Set up local-only development
- D: Configure Docker Compose deployment
- E: Wait for quota approval and retry deployment

Just let me know your preference! 🚀
EOF
}

# Run main function
main "$@"
