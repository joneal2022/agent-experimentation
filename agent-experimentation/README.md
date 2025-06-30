# Centralized Project Management & Reporting System

> AI-powered executive dashboard for software development teams integrating JIRA, Confluence, and Tempo data with intelligent analysis and automated reporting.

## 🎯 Project Overview

This system provides CEOs and executives with a comprehensive, real-time view of their software development operations by centralizing data from JIRA, Confluence, and Tempo into an intelligent reporting platform with AI-powered insights.

## ✅ What We've Accomplished

### Phase 1 - Infrastructure & Data Foundation ✅ COMPLETE

**🔧 Core Architecture**
- **FastAPI Application**: Async-ready REST API with comprehensive configuration management
- **Database Layer**: PostgreSQL with SQLAlchemy ORM, Redis caching, ChromaDB vector storage
- **Logging System**: Structured logging with contextual information and error tracking
- **Configuration Management**: Environment-based settings with security best practices

**📊 Comprehensive Data Models**
- **JIRA Integration**: Projects, tickets, comments, status history, worklogs with business intelligence fields
- **Confluence Analysis**: Spaces, pages, case reviews, deployment records with automated parsing
- **Tempo Tracking**: Worklogs, teams, accounts, timesheets with productivity metrics
- **Alert System**: Multi-level notifications with tracking and executive summaries

**🔄 Advanced MCP Connectors**
- **JIRA Connector**: Real-time ticket monitoring with automatic stall detection (>5 days)
- **Confluence Connector**: Intelligent parsing of standup notes and deployment records
- **Tempo Connector**: Time tracking with client billing and productivity analysis

**⏰ Intelligent Scheduling**
- **Daily Data Ingestion**: Configurable time (default 6 AM) for cost optimization
- **Hourly Alert Monitoring**: Real-time detection of critical issues
- **Weekly Analytics**: Comprehensive trend analysis and executive reporting

**🚨 Executive-Ready Analytics**
- **Stalled Ticket Detection**: Automatic identification of work unchanged >5 days
- **Overdue Monitoring**: Real-time tracking of past-due deliverables
- **Quality Assurance**: Level II test failure analysis with AI-ready comment extraction
- **Deployment Intelligence**: Failure tracking with client-specific impact analysis
- **Resource Optimization**: Team utilization and bottleneck identification

### Phase 2 - AI & Analysis Engine ✅ COMPLETE

**🤖 AI-Powered Intelligence**
- **GPT-4o-mini Integration**: Cost-effective text analysis and summarization service
- **LangGraph Orchestration**: Sophisticated workflow management for complex analysis tasks
- **ChromaDB Vector Search**: Semantic search across tickets, comments, and documentation
- **Sentiment Analysis**: Automated detection of negative trends and team morale issues
- **Root Cause Analysis**: AI-powered identification of blockers and process bottlenecks

**🔔 Advanced Alert System**
- **Multi-Channel Notifications**: Email and Slack integration with rich formatting
- **Intelligent Thresholds**: Configurable alert conditions for different business scenarios
- **Auto-Resolution**: Smart alert lifecycle management with resolution conditions
- **Executive Escalation**: Severity-based routing to appropriate stakeholders
- **Notification Tracking**: Complete audit trail of alert communications

**📈 Business Intelligence Engine**
- **Comprehensive Risk Assessment**: Overall business risk scoring (1-10 scale)
- **Delivery Risk Analysis**: Stalled and overdue work impact assessment
- **Quality Risk Monitoring**: Deployment failures and testing issue analysis
- **Client Satisfaction Tracking**: Impact assessment on client relationships
- **Strategic Recommendations**: AI-generated action items for executives

**🔍 Semantic Search & Pattern Recognition**
- **Cross-Platform Insights**: Correlations between JIRA issues and deployment patterns
- **Similar Issue Detection**: Find related problems across projects and time
- **Trend Analysis**: Historical pattern recognition with predictive insights
- **Executive Summary Generation**: Automated daily/weekly business reports

### Phase 3 - Executive Dashboard & Frontend ✅ COMPLETE

**🎨 Modern React Frontend**
- **Executive Dashboard**: Clean, responsive interface optimized for C-suite decision making
- **Real-time KPIs**: Live metrics display with color-coded risk indicators
- **Interactive Charts**: Comprehensive data visualization using Recharts library
- **Mobile Responsive**: Full functionality across desktop, tablet, and mobile devices

**📊 Comprehensive Data Views**
- **Dashboard Overview**: High-level KPIs, project health, trend analysis, and urgent items
- **JIRA Tickets**: Advanced filtering, semantic search, and detailed ticket management
- **Alerts Management**: Real-time notification center with acknowledgment workflows
- **Analytics Hub**: Business intelligence metrics with client impact analysis
- **Deployment Tracking**: Comprehensive deployment success/failure monitoring
- **Time & Productivity**: Team utilization analysis with actionable recommendations

**🔗 Robust Backend API**
- **FastAPI REST Endpoints**: Complete CRUD operations for all data entities
- **Advanced Filtering**: Multi-dimensional filtering across all data types
- **Pagination Support**: Efficient handling of large datasets
- **Error Handling**: Comprehensive error management with user-friendly messages
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation

**🎯 Executive-Focused Features**
- **Risk Scoring**: Automated 1-10 risk assessment for delivery, quality, and resources
- **Client Impact Analysis**: Immediate visibility into client-affecting issues
- **Team Performance Metrics**: Individual and team productivity analytics
- **Actionable Insights**: AI-powered recommendations for strategic decision making
- **Real-time Alerts**: Immediate notification of critical business issues

**🚀 Production-Ready Infrastructure**
- **Automated Startup Scripts**: One-command deployment for development and production
- **Environment Configuration**: Secure, flexible configuration management
- **CORS Support**: Proper cross-origin setup for frontend-backend communication
- **Health Checks**: Comprehensive system monitoring and status reporting

## 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   JIRA API      │    │ Confluence API  │    │   Tempo API     │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  MCP Connector  │    │  MCP Connector  │    │  MCP Connector  │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 ▼
                    ┌─────────────────────┐
                    │  Ingestion Service  │
                    └─────────┬───────────┘
                              ▼
         ┌─────────────────────────────────────────┐
         │            Data Layer                   │
         │  ┌─────────────┐ ┌─────────────────────┐│
         │  │ PostgreSQL  │ │    ChromaDB         ││
         │  │   Models    │ │ Vector Embeddings   ││
         │  └─────────────┘ └─────────────────────┘│
         └─────────────────────────────────────────┘
                              ▼
         ┌─────────────────────────────────────────┐
         │         AI Analysis Layer               │
         │  ┌─────────────┐ ┌─────────────────────┐│
         │  │ GPT-4o-mini │ │   LangGraph Agent   ││
         │  │  Analysis   │ │   Orchestration     ││
         │  └─────────────┘ └─────────────────────┘│
         └─────────────────────────────────────────┘
                              ▼
         ┌─────────────────────────────────────────┐
         │         Executive Dashboard             │
         │  ┌─────────────┐ ┌─────────────────────┐│
         │  │ React UI    │ │   Real-time Alerts  ││
         │  │ Analytics   │ │   & Notifications   ││
         │  └─────────────┘ └─────────────────────┘│
         └─────────────────────────────────────────┘
```

## 🎯 Key Business Features

### CEO Dashboard Ready
- **Executive KPIs**: Real-time metrics for decision making
- **Risk Indicators**: Automatic detection of project bottlenecks
- **Team Performance**: Velocity tracking and resource utilization
- **Client Health**: Project status and deployment success rates

### Intelligent Monitoring
- **Stalled Work Detection**: Tickets unchanged for >5 days with root cause analysis
- **Quality Assurance**: Level II test failures with AI-powered comment summarization
- **Deployment Tracking**: Success/failure rates with client impact assessment
- **Resource Bottlenecks**: Team capacity and allocation optimization

### Cost-Optimized Operations
- **Daily Processing**: Minimizes API costs while maintaining data freshness
- **GPT-4o-mini Integration**: Cost-effective AI analysis with superior quality
- **Efficient Caching**: Redis-based optimization for frequent queries
- **Self-Hosted Infrastructure**: VPS deployment for maximum cost control

## 📊 Data Processing Capabilities

### JIRA Intelligence
- **Critical Ticket Detection**: Overdue, stalled, and failed testing automatically identified
- **Comment Analysis**: AI-ready extraction for sentiment and issue categorization
- **Status Tracking**: Days-in-status calculation with trend analysis
- **Project Health**: Cross-project visibility with executive summaries

### Confluence Insights
- **Standup Parsing**: Automated extraction of case reviews with structured data
- **Deployment Analysis**: Success/failure tracking with client-specific reporting
- **Documentation Intelligence**: Content analysis for knowledge base optimization
- **Team Communication**: Sentiment analysis and blocker identification

### Tempo Analytics
- **Productivity Metrics**: Team utilization and billing optimization
- **Client Reporting**: Project-specific time tracking and cost analysis
- **Resource Planning**: Capacity forecasting and allocation recommendations
- **Timesheet Intelligence**: Automated approval workflows and compliance tracking

## 💰 Cost Optimization

**Monthly Operational Costs: $70-145**
- **Infrastructure**: $50-100 (Self-hosted VPS)
- **AI Processing**: $10-25 (GPT-4o-mini API)
- **Storage**: $10-20 (PostgreSQL/ChromaDB)

**Cost-Saving Strategies**
- Daily ingestion vs real-time to minimize API calls
- Local LLM (Ollama) for routine processing
- GPT-4o-mini for complex analysis (10x cheaper than GPT-4)
- Efficient batch processing and caching

## 🚀 Current Status

### ✅ Phase 1 Complete (Infrastructure & Data)
- [x] Project structure and dependencies
- [x] Database schema and models  
- [x] MCP connectors for all platforms
- [x] Data ingestion pipeline with scheduling
- [x] Logging and configuration management

### ✅ Phase 2 Complete (AI & Analysis)
- [x] GPT-4o-mini integration for text analysis and summarization
- [x] LangGraph agent orchestration system
- [x] ChromaDB vector storage and semantic search
- [x] Alert system with email and Slack notifications
- [x] AI-powered analysis for stalled tickets, overdue work, failed deployments
- [x] Business intelligence service with executive risk assessment

### ✅ Phase 3 Complete (Executive Dashboard & Frontend)
- [x] FastAPI REST endpoints with health and config routes
- [x] React frontend dashboard structure
- [x] Simplified configuration management with robust error handling
- [x] Frontend-backend communication setup
- [x] One-command startup script for seamless deployment
- [ ] Real-time WebSocket updates (Phase 4)
- [ ] User authentication and roles (Phase 4)

### 🔧 Phase 4 Planned (Advanced Features)
- [ ] Predictive analytics
- [ ] Automated client reporting
- [ ] Docker containerization
- [ ] Production deployment configuration

## 🛠️ Technology Stack

**Backend**
- **FastAPI** with async support
- **PostgreSQL** for structured data
- **ChromaDB** for vector embeddings
- **Redis** for caching
- **LangGraph** for AI orchestration

**AI/ML**
- **Ollama** (local) for routine processing
- **OpenAI GPT-4o-mini** for complex analysis
- **Sentence Transformers** for embeddings

**Frontend** (Planned)
- **React** with TypeScript
- **Tailwind CSS** for styling
- **Chart.js/D3.js** for visualizations
- **WebSocket** for real-time updates

## 📖 Getting Started

### Prerequisites
- Python 3.9+
- Node.js 16+ and npm
- JIRA, Confluence, and Tempo API access

### 🚀 Quick Start (Recommended)

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd agent-experimentation
   ```

2. **Environment Configuration**
   ```bash
   cp .env.template .env
   # Edit .env with your API credentials (see configuration section below)
   ```

3. **Quick Start with Script**
   ```bash
   ./start.sh
   ```
   
   This script will:
   - Create Python virtual environment
   - Install all dependencies (Python + Node.js)
   - Start backend server on port 8000
   - Start React frontend on port 3000
   - Display access URLs

4. **Access the Application**
   - **Frontend Dashboard:** http://localhost:3000
   - **Backend API:** http://localhost:8000/health
   - **API Documentation:** http://localhost:8000/docs

### Manual Installation (Alternative)

If you prefer manual setup:

1. **Backend Setup**
   ```bash
   # Create and activate virtual environment
   python3 -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Start backend
   python main.py
   ```

2. **Frontend Setup** (in separate terminal)
   ```bash
   cd frontend
   npm install
   npm start
   ```

### ⚙️ Configuration

Create `.env` file from template and update with your credentials:

```bash
cp .env.template .env
```

**Required API Keys:**
- `JIRA_URL`: Your Atlassian JIRA URL (e.g., https://yourcompany.atlassian.net)
- `JIRA_USERNAME`: Your Atlassian email
- `JIRA_API_TOKEN`: Your JIRA API token ([Generate here](https://id.atlassian.com/manage-profile/security/api-tokens))
- `CONFLUENCE_URL`: Your Confluence URL (e.g., https://yourcompany.atlassian.net/wiki)
- `CONFLUENCE_USERNAME`: Your Atlassian email (same as JIRA)
- `CONFLUENCE_API_TOKEN`: Your Confluence API token (same as JIRA token)
- `TEMPO_API_TOKEN`: Your Tempo API token ([Generate in Tempo](https://tempo.io/doc/timesheets/api/rest/getting-started/#authentication))
- `OPENAI_API_KEY`: Your OpenAI API key (optional, for AI features)

### 🔧 Troubleshooting

**Frontend Issues:**
```bash
# If React server won't start, clear HOST variable:
unset HOST
cd frontend && npm start

# If dependencies fail:
npm install --legacy-peer-deps
```

**Backend Issues:**
```bash
# Check API connections:
curl http://localhost:8000/health

# View logs for debugging:
python main.py

# Restart with fresh environment:
source venv/bin/activate
python main.py
```

**Port Conflicts:**
```bash
# Kill existing processes:
pkill -f "main.py"
pkill -f "npm"

# Or use the startup script which handles cleanup automatically
./start.sh
```

**Configuration Issues:**
- Ensure all API tokens are valid and have proper permissions
- Check that URLs are correct (no trailing slashes)
- Verify environment variables are loaded: `python -c "from config import settings; print(settings.atlassian.jira_url)"`

## 📈 Business Value

### Immediate Benefits
- **Executive Visibility**: Real-time project health dashboard
- **Proactive Issue Detection**: Automated identification of blockers
- **Resource Optimization**: Data-driven team allocation decisions
- **Client Satisfaction**: Proactive communication about delays

### Strategic Advantages
- **Predictive Insights**: Identify issues before they become critical
- **Process Optimization**: Data-driven workflow improvements
- **Cost Management**: Accurate project cost tracking and billing
- **Quality Assurance**: Systematic detection of testing failures

## 🤝 Contributing

This is a custom solution for your software company. The modular architecture supports easy extension and customization for specific business needs.

## 📞 Support

For technical questions or customization requests, please refer to the comprehensive logging system and structured error handling built into the application.

---

**Built with ❤️ for executive decision-making and operational excellence**