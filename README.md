# LeetCode AI Agent

A comprehensive AI-powered platform for mastering LeetCode problems through intelligent analysis, automated tutorial generation, and personalized learning paths. Transform any LeetCode problem into structured learning content with AI-driven insights.

## Features

### 🤖 **AI-Powered Analysis**
- **Problem Crawler**: Automatically fetch all LeetCode problems with metadata, descriptions, and examples
- **Intelligent Categorization**: AI analyzes problems to identify topics, patterns, and solution approaches
- **Pattern Recognition**: Automatically discover and classify algorithmic patterns across problems

### 📚 **Content Generation**
- **Tutorial Generator**: Create comprehensive pattern-specific tutorials with examples and practice problems
- **Solution Generator**: Generate detailed step-by-step solutions with multiple approaches
- **Study Plans**: Personalized learning paths based on your progress and goals

### 🎯 **Personalized Learning**
- **Progress Tracking**: Monitor mastery of patterns and topics over time
- **Smart Recommendations**: Get tailored practice suggestions based on your weak areas
- **Adaptive Study Plans**: 7-day personalized study schedules that adapt to your progress

### 💬 **Intelligent Q&A Agent**
- **RAG-Powered Responses**: Search through patterns, tutorials, and solutions for comprehensive answers
- **Context-Aware**: Understands your skill level and learning preferences
- **Instant Help**: Get explanations, examples, and practice recommendations on demand

### ☁️ **Cloud-Native Architecture**
- **Azure CosmosDB**: Scalable NoSQL storage for problems, patterns, and user progress
- **Azure Blob Storage**: Reliable storage for tutorials and solutions
- **Azure OpenAI**: Advanced AI analysis and content generation

## Prerequisites

- Python 3.10 or newer
- Azure subscription (for cloud storage and AI services)
- OpenAI API access (for AI analysis and content generation)

## Getting Started

### 1. Azure Setup

First, set up your Azure resources:

1. **Create Azure Resources**:
   - CosmosDB account with a database named `leetcode-agent`
   - Storage account with a container named `tutorials`
   - OpenAI resource (or use OpenAI directly)

2. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your Azure credentials
   ```

   Required environment variables:
   ```env
   # Azure Configuration
   AZURE_COSMOS_ENDPOINT=https://your-cosmos.documents.azure.com:443/
   AZURE_COSMOS_KEY=your-cosmos-key
   AZURE_STORAGE_ACCOUNT=your-storage-account
   AZURE_STORAGE_KEY=your-storage-key

   # OpenAI Configuration
   OPENAI_API_KEY=your-openai-key
   OPENAI_MODEL=gpt-4
   ```

### 2. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the Application

```bash
python app.py
```

The application starts on [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Usage Guide

### 🚀 **Initial Setup**

1. **Crawl LeetCode Problems**:
   ```bash
   curl -X POST http://localhost:5000/api/crawl-problems
   ```
   This fetches all LeetCode problems and saves them to Azure CosmosDB.

2. **Analyze Problems with AI**:
   ```bash
   curl -X POST http://localhost:5000/api/analyze-problems
   ```
   AI analyzes each problem to identify patterns, topics, and solution approaches.

3. **Generate Tutorials**:
   ```bash
   curl -X POST http://localhost:5000/api/generate-tutorials
   ```
   Creates comprehensive tutorials for each identified pattern.

4. **Generate Solutions**:
   ```bash
   curl -X POST http://localhost:5000/api/generate-solutions
   ```
   Generates detailed solutions for problems.

### 🎯 **Interactive Features**

#### Q&A Agent
```bash
curl -X POST http://localhost:5000/api/ask-agent \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I solve two pointer problems?", "user_context": {"skill_level": "intermediate"}}'
```

#### Progress Tracking
```bash
# Get user progress
curl http://localhost:5000/api/user-progress/user123

# Update progress after solving a problem
curl -X POST http://localhost:5000/api/user-progress/user123/update \
  -H "Content-Type: application/json" \
  -d '{"problem_id": "1", "success": true, "time_spent": 25, "attempts": 2}'

# Get personalized recommendations
curl http://localhost:5000/api/user-progress/user123/recommendations

# Get study plan
curl "http://localhost:5000/api/user-progress/user123/study-plan?days=7"
```

#### Content Access
```bash
# Get tutorial for a pattern
curl http://localhost:5000/api/tutorial/Two%20Pointers

# Get solution for a problem
curl http://localhost:5000/api/solution/1
```

## 🚀 **Deployment**

### **🎯 Quick Start - One Command Deployment**

Use the comprehensive deployment script that handles everything:

```bash
# Deploy everything and run crawler
./deploy-and-crawl.sh -g my-leetcode-agent-rg

# Deploy only (no crawler)
./deploy-and-crawl.sh -g my-leetcode-agent-rg --deploy-only

# Deploy with FREE TIER (no quota needed)
./deploy-and-crawl.sh -g my-leetcode-agent-rg --free-tier

# Cleanup everything
./deploy-and-crawl.sh -g my-leetcode-agent-rg --cleanup-only

# Deploy but skip crawler
./deploy-and-crawl.sh -g my-leetcode-agent-rg --skip-crawl
```

**Prerequisites:**
1. **Azure CLI**: `az login` to authenticate
2. **OpenAI API Key**: Add to `.env` file after deployment
3. **Permissions**: Azure subscription with resource creation permissions

**Quota Requirements:**
- **Standard Deployment**: Requires Basic VM quota (App Service B1 instances)
- **Free Tier Deployment**: No quota required (`--free-tier` option)

**If you encounter quota errors:**
```bash
# Use free tier (no quota needed)
./deploy-and-crawl.sh -g my-leetcode-agent-rg --free-tier

# Or request quota increase
./request-quota.sh
```

### **Validation & Monitoring**

After deployment, validate everything is working:

```bash
# Comprehensive deployment validation
./validate-deployment.sh -g my-leetcode-agent-rg

# Check specific components
az resource list --resource-group my-leetcode-agent-rg --query "[].{name:name, type:type, status:provisioningState}" -o table
az webapp list --resource-group my-leetcode-agent-rg --query "[].{name:name, state:state}" -o table

# Monitor web app logs
az webapp log tail --name your-webapp-name --resource-group my-leetcode-agent-rg

# Test API endpoints
curl https://your-webapp-name.azurewebsites.net/api/system-status
```

### **🔧 Manual Deployment Options**

#### **Option 1: Automated Azure Deployment**

1. **Deploy Infrastructure:**
   ```bash
   cd infrastructure

   # Using PowerShell (Windows)
   .\deploy.ps1 -ResourceGroupName "my-leetcode-agent-rg" -Location "East US" -Environment "dev"

   # Using Bash (Linux/Mac)
   ./deploy.sh --resource-group my-leetcode-agent-rg --location "East US" --environment dev
   ```

2. **Deploy Application:**
   ```bash
   # Build and deploy to Azure Web App
   az webapp up --resource-group my-leetcode-agent-rg --name leetcode-agent-app --src-path .
   ```

#### **Option 2: Docker Deployment**

```bash
# Local development
docker-compose up -d

# Production deployment
docker build -t leetcode-agent .
docker run -p 8000:8000 --env-file .env leetcode-agent
```

#### **Option 3: CI/CD Pipeline**

The GitHub Actions workflow automatically deploys on push to main branch. Configure these secrets in your GitHub repository:

- `AZURE_CREDENTIALS`: Azure service principal credentials
- `ACR_LOGIN_SERVER`: Azure Container Registry URL
- `ACR_USERNAME`: ACR username
- `ACR_PASSWORD`: ACR password

### **📋 Deployment Script Features**

The `deploy-and-crawl.sh` script provides:

#### **🏗️ Complete Infrastructure Deployment**
- Creates Azure resource group
- Deploys CosmosDB, Blob Storage, OpenAI, App Service
- Updates `.env` file with deployment outputs
- Configures all necessary permissions and networking

#### **🐳 Application Deployment**
- Builds Docker container
- Deploys to Azure Web App
- Runs health checks
- Provides real-time deployment status

#### **🤖 Intelligent Crawling**
- Starts MCP server automatically
- Crawls LeetCode problems via official APIs
- Runs AI analysis on problems
- Generates tutorials and solutions
- Shows detailed progress and logs

#### **🧹 Complete Cleanup**
- Deletes entire resource group
- Cleans up local configuration files
- Stops all running services
- Provides confirmation prompts for safety

#### **📊 Real-time Monitoring**
- Color-coded logging (INFO, SUCCESS, WARNING, ERROR)
- Progress indicators for each step
- Detailed API response output
- System health status checks

### **📋 Example Output**

See [`example-output.md`](example-output.md) for a complete example of what the deployment script outputs, including:
- Full deployment walkthrough
- Crawler execution with real API responses
- Cleanup process
- Troubleshooting tips
- Cost estimation

### **✅ Validation Script Features**

The `validate-deployment.sh` script performs comprehensive checks:

#### **🔍 Infrastructure Validation**
- Azure CLI authentication and installation
- Resource group existence and location
- All Azure resource provisioning states
- Service endpoint accessibility

#### **🖥️ Application Validation**
- Web app deployment and configuration
- API endpoint accessibility and responses
- System health status
- Runtime environment checks

#### **☁️ Cloud Service Validation**
- CosmosDB connectivity and databases
- Storage account and containers
- Azure OpenAI endpoint access
- Application Insights setup

#### **📊 Reporting & Diagnostics**
- Color-coded results (PASS/FAIL/WARN)
- Detailed error messages and fix suggestions
- Resource inventory and status summary
- Next steps and troubleshooting guidance

**Usage:**
```bash
./validate-deployment.sh -g my-leetcode-agent-rg          # Standard validation
./validate-deployment.sh -g my-leetcode-agent-rg -v       # Verbose output
./validate-deployment.sh -g my-leetcode-agent-rg --webapp my-app  # Specify webapp
```

### **MCP Server Integration**

The system now integrates with the [leetcode-mcp-server](https://github.com/jinzcdev/leetcode-mcp-server) for comprehensive data access.

#### **Enhanced Data Sources**

| Data Type | MCP Server | Custom Crawler | Status |
|-----------|------------|----------------|---------|
| **Problem Metadata** | ✅ Full API access | ✅ Basic scraping | **Replaced with MCP** |
| **Problem Content** | ✅ Structured data | ✅ HTML parsing | **Replaced with MCP** |
| **Community Solutions** | ✅ Full access | ❌ Not available | **✅ New Feature** |
| **User Profiles** | ✅ Complete data | ❌ Not available | **✅ New Feature** |
| **Contest Rankings** | ✅ Detailed stats | ❌ Not available | **✅ New Feature** |
| **Submission History** | ✅ Full history | ❌ Not available | **✅ New Feature** |
| **User Notes** | ✅ CRUD operations | ❌ Not available | **✅ New Feature** |

#### **MCP Server Setup**

```bash
# Install MCP server globally
npm install -g @jinzcdev/leetcode-mcp-server

# Run MCP server (requires authentication for user data)
export LEETCODE_SESSION="your_leetcode_session_cookie"
leetcode-mcp-server --port 3333
```

### **📊 **Complete API Endpoints**

#### **Core Functionality**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/crawl-problems` | POST | Fetch problems via MCP server |
| `/api/analyze-problems` | POST | AI analyze existing problems |
| `/api/generate-tutorials` | POST | Generate pattern tutorials |
| `/api/generate-solutions` | POST | Generate problem solutions |
| `/api/ask-agent` | POST | Ask the intelligent agent |
| `/api/tutorial/<pattern>` | GET | Get pattern tutorial |
| `/api/solution/<id>` | GET | Get problem solution |

#### **Progress Tracking**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/user-progress/<id>` | GET | Get user progress |
| `/api/user-progress/<id>/update` | POST | Update user progress |
| `/api/user-progress/<id>/recommendations` | GET | Get learning recommendations |
| `/api/user-progress/<id>/study-plan` | GET | Get personalized study plan |
| `/api/user-progress/<id>/mastered-patterns` | GET | Get mastered patterns |

#### **MCP Server Integration**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/problem-solutions/<slug>` | GET | Get community solutions |
| `/api/solution/<id>` | GET | Get detailed solution content |
| `/api/user-profile/<username>` | GET | Get user profile |
| `/api/user-contest-ranking/<username>` | GET | Get contest rankings |
| `/api/user-submissions/<username>` | GET | Get user submissions |
| `/api/problem-progress` | GET | Get solving progress |
| `/api/notes/search` | GET | Search user notes |
| `/api/notes/problem/<id>` | GET | Get problem notes |
| `/api/notes` | POST | Create note |
| `/api/notes/<id>` | PUT | Update note |
| `/api/metadata/categories` | GET | Get problem categories |
| `/api/metadata/tags` | GET | Get problem tags |
| `/api/metadata/languages` | GET | Get supported languages |

#### **System Management**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/system-status` | GET | Get system health status |
| `/api/refresh` | POST | Refresh local data |

### 4. Run automated checks

A small Pytest suite exercises the Flask endpoints so you can confirm the backend is serving valid responses:

```bash
pytest
```

You can also perform a quick syntax check to ensure the project imports cleanly:

```bash
python -m compileall .
```

Running both commands before making changes helps catch regressions early.

### 5. Extending the dataset

To analyse additional problems, append entries to `data/problems.json`. Each problem supports the following fields:

- `id`: Numerical identifier (not required to match real LeetCode IDs, but should be unique).
- `title`: Problem name.
- `url`: Direct link to the problem statement.
- `difficulty`: One of `Easy`, `Medium`, or `Hard`.
- `topic`: Primary category such as `Array`, `Graph`, or `Dynamic Programming`.
- `patterns`: Array of key techniques leveraged in the solution.
- `summary`: One-sentence explanation of the core idea.
- `key_steps`: Bullet-point breakdown for the solution approach.

Click **Refresh insights** at any time to force the backend to reload data from the MCP server (or the local JSON if you are offline). The backend automatically recalculates category distributions, pattern spotlights, and the guided tutorial each time data is reloaded.

## Project structure

```
.
├── app.py               # Flask application with analysis endpoints
├── data/
│   └── problems.json    # Curated LeetCode problem sample used for insights
├── static/
│   ├── app.js           # Frontend logic fetching data and rendering UI
│   ├── index.html       # Main dashboard layout
│   └── styles.css       # Styling for the interface
├── tests/
│   └── test_app.py      # Automated endpoint smoke tests
└── README.md
```

## Troubleshooting tips

- **The dashboard shows no data** – ensure `data/problems.json` exists or that the MCP server is reachable. Check the Flask logs for fetch errors.
- **`pytest` cannot import Flask** – double-check that the virtual environment is activated and `pip install -r requirements.txt` completed successfully.
- **CORS or browser errors** – the frontend is served by Flask, so load the app through `http://127.0.0.1:5000/` rather than opening `static/index.html` directly.

With these steps you can run the dashboard locally, validate the API surface, and iterate on additional insights confidently.
└── README.md
```

## Extending the dataset

To analyse additional problems, append entries to `data/problems.json`. Each problem supports the following fields:

- `id`: Numerical identifier (not required to match real LeetCode IDs, but should be unique).
- `title`: Problem name.
- `url`: Direct link to the problem statement.
- `difficulty`: One of `Easy`, `Medium`, or `Hard`.
- `topic`: Primary category such as `Array`, `Graph`, or `Dynamic Programming`.
- `patterns`: Array of key techniques leveraged in the solution.
- `summary`: One-sentence explanation of the core idea.
- `key_steps`: Bullet-point breakdown for the solution approach.

Click **Refresh insights** at any time to force the backend to reload data from the MCP server (or the local JSON if you are offline). The backend automatically recalculates category distributions, pattern spotlights, and the guided tutorial each time data is reloaded.
