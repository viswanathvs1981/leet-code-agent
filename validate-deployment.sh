#!/bin/bash

# LeetCode AI Agent - Comprehensive Deployment Validation Script
# This script validates all components of the deployed system

set -e

# Configuration
RESOURCE_GROUP_NAME=""
LOCATION="East US"
WEBAPP_NAME=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Validation counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Logging functions
log_header() {
    echo -e "\n${BOLD}${CYAN}================================${NC}"
    echo -e "${BOLD}${CYAN} $1 ${NC}"
    echo -e "${BOLD}${CYAN}================================${NC}\n"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED_CHECKS++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARNING_CHECKS++))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED_CHECKS++))
}

log_check() {
    ((TOTAL_CHECKS++))
    echo -e "${CYAN}[CHECK $TOTAL_CHECKS]${NC} $1"
}

# Show usage
show_usage() {
    echo "LeetCode AI Agent - Deployment Validation Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -g, --resource-group NAME    Azure resource group name (required)"
    echo "  -l, --location LOCATION      Azure region (default: East US)"
    echo "  -w, --webapp NAME           Web app name (optional, auto-detected)"
    echo "  -v, --verbose               Verbose output"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -g my-leetcode-agent-rg                    # Validate deployment"
    echo "  $0 -g my-leetcode-agent-rg -v                 # Verbose validation"
    echo "  $0 -g my-leetcode-agent-rg --webapp my-app    # Specify webapp name"
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
            -w|--webapp)
                WEBAPP_NAME="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=true
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
    if [[ -z "$RESOURCE_GROUP_NAME" ]]; then
        log_error "Resource group name is required (use -g or --resource-group)"
        show_usage
        exit 1
    fi
}

# Validate Azure CLI and authentication
validate_azure_cli() {
    log_check "Azure CLI Installation"

    if ! command -v az &> /dev/null; then
        log_error "Azure CLI is not installed"
        log_info "Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        return 1
    fi

    log_success "Azure CLI is installed"

    log_check "Azure Authentication"

    if ! az account show &> /dev/null; then
        log_error "Not authenticated with Azure CLI"
        log_info "Run: az login"
        return 1
    fi

    local account_info=$(az account show --query "{name:name, user:user.name}" -o tsv 2>/dev/null)
    log_success "Authenticated as: $account_info"
}

# Validate resource group
validate_resource_group() {
    log_check "Resource Group Existence"

    local rg_exists=$(az group exists --name "$RESOURCE_GROUP_NAME" 2>/dev/null)

    if [[ "$rg_exists" != "true" ]]; then
        log_error "Resource group '$RESOURCE_GROUP_NAME' does not exist"
        return 1
    fi

    log_success "Resource group '$RESOURCE_GROUP_NAME' exists"

    log_check "Resource Group Location"

    local rg_location=$(az group show --name "$RESOURCE_GROUP_NAME" --query "location" -o tsv 2>/dev/null)

    if [[ "$rg_location" != "$(echo $LOCATION | tr '[:upper:]' '[:lower:]')" ]]; then
        log_warning "Resource group location ($rg_location) differs from expected ($LOCATION)"
    else
        log_success "Resource group location is correct: $rg_location"
    fi
}

# Validate Azure resources
validate_resources() {
    log_check "Azure Resources Overview"

    local resources=$(az resource list --resource-group "$RESOURCE_GROUP_NAME" --query "[].{name:name, type:type, status:provisioningState}" -o json 2>/dev/null)

    if [[ -z "$resources" ]] || [[ "$resources" == "[]" ]]; then
        log_error "No resources found in resource group '$RESOURCE_GROUP_NAME'"
        log_info "The deployment may have failed or not completed"
        return 1
    fi

    local resource_count=$(echo "$resources" | jq length 2>/dev/null || echo "0")
    log_success "Found $resource_count resources in resource group"

    # Parse and validate each resource type
    validate_cosmos_db "$resources"
    validate_storage_account "$resources"
    validate_openai "$resources"
    validate_web_app "$resources"
    validate_app_insights "$resources"
}

# Validate CosmosDB
validate_cosmos_db() {
    local resources="$1"

    log_check "CosmosDB Database"

    local cosmos_name=$(echo "$resources" | jq -r '.[] | select(.type == "Microsoft.DocumentDB/databaseAccounts") | .name' 2>/dev/null | head -1)

    if [[ -z "$cosmos_name" ]]; then
        log_error "CosmosDB account not found"
        return 1
    fi

    local cosmos_status=$(echo "$resources" | jq -r ".[] | select(.name == \"$cosmos_name\") | .status" 2>/dev/null)

    if [[ "$cosmos_status" != "Succeeded" ]]; then
        log_error "CosmosDB status: $cosmos_status"
        return 1
    fi

    log_success "CosmosDB '$cosmos_name' is provisioned"

    # Test CosmosDB connectivity
    log_check "CosmosDB Connectivity"

    local cosmos_endpoint=$(az cosmosdb show --name "$cosmos_name" --resource-group "$RESOURCE_GROUP_NAME" --query "documentEndpoint" -o tsv 2>/dev/null)

    if [[ -z "$cosmos_endpoint" ]]; then
        log_error "Cannot retrieve CosmosDB endpoint"
        return 1
    fi

    log_success "CosmosDB endpoint accessible: $cosmos_endpoint"

    # Check databases
    log_check "CosmosDB Databases"

    local databases=$(az cosmosdb sql database list --account-name "$cosmos_name" --resource-group "$RESOURCE_GROUP_NAME" --query "[].id" -o tsv 2>/dev/null)

    if [[ -z "$databases" ]]; then
        log_warning "No databases found in CosmosDB (may be created by application)"
    else
        local db_count=$(echo "$databases" | wc -l | tr -d ' ')
        log_success "Found $db_count databases in CosmosDB"
    fi
}

# Validate Storage Account
validate_storage_account() {
    local resources="$1"

    log_check "Storage Account"

    local storage_name=$(echo "$resources" | jq -r '.[] | select(.type == "Microsoft.Storage/storageAccounts") | .name' 2>/dev/null | head -1)

    if [[ -z "$storage_name" ]]; then
        log_error "Storage account not found"
        return 1
    fi

    local storage_status=$(echo "$resources" | jq -r ".[] | select(.name == \"$storage_name\") | .status" 2>/dev/null)

    if [[ "$storage_status" != "Succeeded" ]]; then
        log_error "Storage account status: $storage_status"
        return 1
    fi

    log_success "Storage account '$storage_name' is provisioned"

    # Check containers
    log_check "Storage Containers"

    local containers=$(az storage container list --account-name "$storage_name" --auth-mode login --query "[].name" -o tsv 2>/dev/null)

    if [[ -z "$containers" ]]; then
        log_warning "No containers found in storage account"
    else
        local container_count=$(echo "$containers" | wc -l | tr -d ' ')
        log_success "Found $container_count containers in storage account"
    fi
}

# Validate Azure OpenAI
validate_openai() {
    local resources="$1"

    log_check "Azure OpenAI"

    local openai_name=$(echo "$resources" | jq -r '.[] | select(.type == "Microsoft.CognitiveServices/accounts") | .name' 2>/dev/null | head -1)

    if [[ -z "$openai_name" ]]; then
        log_error "Azure OpenAI resource not found"
        return 1
    fi

    local openai_status=$(echo "$resources" | jq -r ".[] | select(.name == \"$openai_name\") | .status" 2>/dev/null)

    if [[ "$openai_status" != "Succeeded" ]]; then
        log_error "Azure OpenAI status: $openai_status"
        return 1
    fi

    log_success "Azure OpenAI '$openai_name' is provisioned"

    # Test OpenAI endpoint
    log_check "Azure OpenAI Endpoint"

    local openai_endpoint=$(az cognitiveservices account show --name "$openai_name" --resource-group "$RESOURCE_GROUP_NAME" --query "properties.endpoint" -o tsv 2>/dev/null)

    if [[ -z "$openai_endpoint" ]]; then
        log_error "Cannot retrieve OpenAI endpoint"
        return 1
    fi

    log_success "OpenAI endpoint accessible: $openai_endpoint"
}

# Validate Web App
validate_web_app() {
    local resources="$1"

    log_check "Web App"

    local webapp_name=$(echo "$resources" | jq -r '.[] | select(.type == "Microsoft.Web/sites") | .name' 2>/dev/null | head -1)

    if [[ -z "$webapp_name" ]]; then
        log_error "Web app not found"
        return 1
    fi

    # Override WEBAPP_NAME if not provided
    if [[ -z "$WEBAPP_NAME" ]]; then
        WEBAPP_NAME="$webapp_name"
    fi

    local webapp_status=$(echo "$resources" | jq -r ".[] | select(.name == \"$webapp_name\") | .status" 2>/dev/null)

    if [[ "$webapp_status" != "Succeeded" ]]; then
        log_error "Web app status: $webapp_status"
        return 1
    fi

    log_success "Web app '$webapp_name' is provisioned"

    # Get web app details
    log_check "Web App Configuration"

    local webapp_info=$(az webapp show --name "$webapp_name" --resource-group "$RESOURCE_GROUP_NAME" --query "{url:defaultHostName, state:state, runtime:siteConfig.linuxFxVersion}" -o json 2>/dev/null)

    if [[ -z "$webapp_info" ]]; then
        log_error "Cannot retrieve web app details"
        return 1
    fi

    local webapp_url=$(echo "$webapp_info" | jq -r '.url' 2>/dev/null)
    local webapp_state=$(echo "$webapp_info" | jq -r '.state' 2>/dev/null)
    local webapp_runtime=$(echo "$webapp_info" | jq -r '.runtime' 2>/dev/null)

    log_success "Web app URL: https://$webapp_url"
    log_success "Web app state: $webapp_state"
    log_success "Runtime: $webapp_runtime"

    # Test web app accessibility
    validate_web_app_accessibility "$webapp_url"
}

# Validate Web App accessibility
validate_web_app_accessibility() {
    local webapp_url="$1"

    log_check "Web App Accessibility"

    if curl -f -s --max-time 10 "https://$webapp_url" > /dev/null 2>&1; then
        log_success "Web app is accessible at https://$webapp_url"
    else
        log_error "Web app is not accessible at https://$webapp_url"
        return 1
    fi

    # Test API endpoints
    validate_api_endpoints "$webapp_url"
}

# Validate API endpoints
validate_api_endpoints() {
    local webapp_url="$1"

    log_check "API Endpoints - System Status"

    local system_status=$(curl -s --max-time 10 "https://$webapp_url/api/system-status" 2>/dev/null)

    if [[ -z "$system_status" ]]; then
        log_error "Cannot access system status API"
        return 1
    fi

    # Check if response contains expected fields
    if echo "$system_status" | jq -e '.cosmos_db' > /dev/null 2>&1; then
        log_success "System status API is responding correctly"
    else
        log_error "System status API response is malformed"
        [[ "$VERBOSE" == "true" ]] && echo "Response: $system_status"
        return 1
    fi

    log_check "API Endpoints - Problems"

    local problems_response=$(curl -s --max-time 10 "https://$webapp_url/api/problems" 2>/dev/null)

    if [[ -z "$problems_response" ]]; then
        log_warning "Problems API returned empty response (may not be populated yet)"
    else
        log_success "Problems API is accessible"
    fi

    log_check "API Endpoints - Patterns"

    local patterns_response=$(curl -s --max-time 10 "https://$webapp_url/api/patterns" 2>/dev/null)

    if [[ -z "$patterns_response" ]]; then
        log_warning "Patterns API returned empty response (may not be populated yet)"
    else
        log_success "Patterns API is accessible"
    fi
}

# Validate Application Insights
validate_app_insights() {
    local resources="$1"

    log_check "Application Insights"

    local insights_name=$(echo "$resources" | jq -r '.[] | select(.type == "Microsoft.Insights/components") | .name' 2>/dev/null | head -1)

    if [[ -z "$insights_name" ]]; then
        log_warning "Application Insights not found (optional component)"
        return 0
    fi

    local insights_status=$(echo "$resources" | jq -r ".[] | select(.name == \"$insights_name\") | .status" 2>/dev/null)

    if [[ "$insights_status" != "Succeeded" ]]; then
        log_warning "Application Insights status: $insights_status"
    else
        log_success "Application Insights '$insights_name' is provisioned"
    fi
}

# Validate environment configuration
validate_environment() {
    log_check "Environment Configuration"

    if [[ ! -f ".env" ]]; then
        log_error ".env file not found"
        log_info "Run deployment script to create .env file"
        return 1
    fi

    log_success ".env file exists"

    # Check for required environment variables
    local required_vars=("AZURE_COSMOS_ENDPOINT" "AZURE_COSMOS_KEY" "AZURE_STORAGE_ACCOUNT" "AZURE_STORAGE_KEY" "OPENAI_API_KEY")

    for var in "${required_vars[@]}"; do
        if ! grep -q "^$var=" .env; then
            log_error "Required environment variable '$var' not found in .env"
            return 1
        fi
    done

    log_success "All required environment variables are configured"
}

# Generate validation summary
generate_summary() {
    log_header "VALIDATION SUMMARY"

    echo -e "${CYAN}Total Checks Performed: $TOTAL_CHECKS${NC}"
    echo -e "${GREEN}Passed: $PASSED_CHECKS${NC}"
    echo -e "${YELLOW}Warnings: $WARNING_CHECKS${NC}"
    echo -e "${RED}Failed: $FAILED_CHECKS${NC}"

    echo ""

    if [[ $FAILED_CHECKS -eq 0 ]]; then
        if [[ $WARNING_CHECKS -eq 0 ]]; then
            echo -e "${GREEN}🎉 ALL CHECKS PASSED!${NC}"
            echo -e "${GREEN}Your LeetCode AI Agent deployment is fully operational.${NC}"
        else
            echo -e "${YELLOW}⚠️  DEPLOYMENT SUCCESSFUL WITH WARNINGS${NC}"
            echo -e "${YELLOW}The system is functional but some optional components may need attention.${NC}"
        fi

        echo ""
        echo -e "${CYAN}Next Steps:${NC}"
        echo "1. Access your web app at: https://$WEBAPP_NAME.azurewebsites.net"
        echo "2. Run the crawler: curl -X POST https://$WEBAPP_NAME.azurewebsites.net/api/crawl-problems"
        echo "3. Monitor logs: az webapp log tail --name $WEBAPP_NAME --resource-group $RESOURCE_GROUP_NAME"

    else
        echo -e "${RED}❌ DEPLOYMENT ISSUES DETECTED${NC}"
        echo -e "${RED}Please address the failed checks before proceeding.${NC}"

        echo ""
        echo -e "${CYAN}Common Fixes:${NC}"
        echo "1. Redeploy: ./deploy-and-crawl.sh -g $RESOURCE_GROUP_NAME --cleanup-only && ./deploy-and-crawl.sh -g $RESOURCE_GROUP_NAME --free-tier"
        echo "2. Check quotas: ./request-quota.sh"
        echo "3. Try different region: ./deploy-and-crawl.sh -g $RESOURCE_GROUP_NAME --free-tier -l 'West US 2'"
    fi

    echo ""
    echo -e "${BLUE}Resource Group: $RESOURCE_GROUP_NAME${NC}"
    echo -e "${BLUE}Location: $LOCATION${NC}"
    if [[ -n "$WEBAPP_NAME" ]]; then
        echo -e "${BLUE}Web App: https://$WEBAPP_NAME.azurewebsites.net${NC}"
    fi
}

# Main execution
main() {
    parse_args "$@"

    log_header "🔍 LEETCODE AI AGENT DEPLOYMENT VALIDATION"

    echo "Validating deployment for resource group: $RESOURCE_GROUP_NAME"
    echo "Location: $LOCATION"
    echo ""

    # Run all validations
    validate_azure_cli
    validate_resource_group
    validate_resources
    validate_environment

    # Generate summary
    generate_summary

    # Exit with appropriate code
    if [[ $FAILED_CHECKS -gt 0 ]]; then
        exit 1
    else
        exit 0
    fi
}

# Handle script interruption
trap 'log_error "Validation interrupted by user"; exit 1' INT TERM

# Run main function
main "$@"
