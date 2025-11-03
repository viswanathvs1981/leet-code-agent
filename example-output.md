# Example Deployment Output

This shows what you'll see when running the deployment script.

## Full Deployment with Crawling

```bash
$ ./deploy-and-crawl.sh -g my-leetcode-agent-rg

================================
 Checking Prerequisites
================================

[INFO] Azure CLI is installed
[SUCCESS] Docker is installed
[WARNING] .env file not found. Creating template...
[INFO] Created .env template. Please fill in your OpenAI API key and other credentials.
[SUCCESS] Azure authentication verified

================================
 Deploying Azure Infrastructure
================================

[INFO] Resource Group: my-leetcode-agent-rg
[INFO] Location: East US
[INFO] Environment: dev
[INFO] Creating resource group...
[INFO] Deploying infrastructure with Bicep...
[INFO] Retrieving deployment outputs...
[SUCCESS] Infrastructure deployed successfully!

🔑 Deployment Configuration:
CosmosDB Endpoint: https://leetcode-agent-cosmos-abc123.documents.azure.com:443/
Storage Account: leetcodeagentstorageabc123
OpenAI Endpoint: https://leetcode-agent-openai-abc123.openai.azure.com/
Web App URL: https://leetcode-agent-app.azurewebsites.net

================================
 Deploying Application
================================

[INFO] Building Docker image...
[INFO] Deploying to Azure Web App...
[INFO] Waiting for deployment to complete...
[INFO] Running health check...
[SUCCESS] Application deployed and healthy!

================================
 Running LeetCode Crawler
================================

[INFO] Checking MCP server status...
[WARNING] MCP server not detected. Starting it...
[INFO] Starting LeetCode MCP server...
[INFO] Installing LeetCode MCP server...
[INFO] Starting MCP server on port 3333...
[SUCCESS] MCP server started successfully
[SUCCESS] ✅ MCP Server: Available
[INFO] Waiting for all services to be ready...

🚀 Starting LeetCode crawler...

📥 Step 1: Crawling LeetCode problems...
[SUCCESS] Problems crawled successfully!
{
  "status": "success",
  "problems_fetched": 100,
  "problems_saved": 100,
  "problems_analyzed": 50,
  "patterns_identified": 15,
  "patterns_saved": 15,
  "data_source": "LeetCode MCP Server + AI Analysis",
  "last_refreshed": "2024-12-19T10:30:45"
}

🧠 Step 2: Analyzing problems with AI...
[SUCCESS] Problems analyzed successfully!
{
  "status": "success",
  "problems_analyzed": 100,
  "problems_saved": 100,
  "patterns_identified": 25,
  "patterns_saved": 25
}

📚 Step 3: Generating pattern tutorials...
[SUCCESS] Tutorials generated successfully!
{
  "status": "success",
  "tutorials_generated": 25,
  "patterns": [
    "Two Pointers",
    "Sliding Window",
    "Dynamic Programming",
    "Binary Search",
    "Graph Algorithms"
  ]
}

💡 Step 4: Generating problem solutions...
[SUCCESS] Solutions generated successfully!
{
  "status": "success",
  "solutions_generated": 50,
  "problem_ids": [
    "1", "2", "3", "4", "5"
  ]
}

📊 Final system status:
{
  "cosmos_db": true,
  "blob_storage": true,
  "openai": true,
  "mcp_server": true,
  "total_problems": 100,
  "total_patterns": 25,
  "data_source": "LeetCode MCP Server + AI Analysis",
  "last_refreshed": "2024-12-19T10:45:12"
}

🎉 Crawler execution completed!

================================
 🎉 Deployment Complete!
================================

[SUCCESS] Your LeetCode AI Agent is ready to use!
[INFO] Web App URL: https://leetcode-agent-app.azurewebsites.net
[INFO] To clean up everything, run: ./deploy-and-crawl.sh -g my-leetcode-agent-rg --cleanup-only
```

## Cleanup Output

```bash
$ ./deploy-and-crawl.sh -g my-leetcode-agent-rg --cleanup-only

================================
 Cleaning Up Azure Resources
================================

[WARNING] This will delete the entire resource group 'my-leetcode-agent-rg' and all resources within it!
Are you sure you want to continue? (yes/no): yes
[INFO] Deleting resource group 'my-leetcode-agent-rg'...
[SUCCESS] Cleanup initiated. Resources will be deleted asynchronously.
[INFO] You can check the status with: az group list --query "[?name=='my-leetcode-agent-rg']"
[INFO] Restoring original .env file...
[INFO] Stopping local services...
[SUCCESS] Cleanup completed!
```

## What Happens During Each Step

### 1. Prerequisites Check
- Verifies Azure CLI, Docker installation
- Creates `.env` template if missing
- Ensures Azure authentication

### 2. Infrastructure Deployment
- Creates resource group
- Deploys via Bicep template:
  - CosmosDB (problems, patterns, user progress)
  - Blob Storage (tutorials, solutions)
  - OpenAI service (AI analysis)
  - App Service (web application)
  - Application Insights (monitoring)

### 3. Application Deployment
- Builds Docker image
- Deploys to Azure Web App
- Runs health checks

### 4. Intelligent Crawling
- **MCP Server**: Automatically starts the LeetCode MCP server
- **Problem Crawling**: Fetches 100 problems via official APIs
- **AI Analysis**: GPT-4 analyzes problems for patterns/topics
- **Tutorial Generation**: Creates comprehensive pattern tutorials
- **Solution Generation**: Generates step-by-step solutions

### 5. System Verification
- Checks all services are healthy
- Displays final statistics
- Provides access URLs

## Real-time Progress Indicators

The script shows:
- ✅ **SUCCESS**: Operations completed successfully
- ⚠️ **WARNING**: Non-critical issues (will continue)
- ❌ **ERROR**: Critical failures (will stop)
- 🔵 **INFO**: Progress updates and status information

## Cost Estimation

Typical monthly costs for a small deployment:
- **CosmosDB**: $25-50 (400 RU/s, minimal usage)
- **Blob Storage**: $1-5 (hot tier, tutorials/solutions)
- **OpenAI**: $20-100 (GPT-4 API calls for analysis)
- **App Service**: $15-50 (Basic B1 plan)
- **Total**: ~$60-200/month depending on usage

## Troubleshooting

If deployment fails:
1. Check Azure CLI authentication: `az account show`
2. Verify resource group permissions
3. Check `.env` file has required API keys
4. Review Azure subscription limits/quotas
5. Check deployment logs: `az deployment group show -g <rg> -n <deployment-name>`
