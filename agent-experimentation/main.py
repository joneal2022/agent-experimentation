"""
MCP Dashboard Backend - Real Data Integration
This backend integrates with JIRA, Tempo, and Confluence via MCP connectors
"""
import uvicorn
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from connectors.jira import JiraMCPConnector
from connectors.tempo import TempoMCPConnector
from connectors.confluence import ConfluenceMCPConnector

app = FastAPI(
    title="MCP Dashboard API",
    description="Executive Dashboard with Real MCP Data Integration",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global connector instances
jira_connector = JiraMCPConnector()
tempo_connector = TempoMCPConnector()
confluence_connector = ConfluenceMCPConnector()

# Cache for dashboard data
dashboard_cache = {}
cache_expiry = None

@app.on_event("startup")
async def startup_event():
    """Initialize MCP connections on startup"""
    print("🚀 Starting MCP Dashboard with real data integrations...")
    
    # Test all connections
    connections = {}
    
    print("🔗 Testing JIRA connection...")
    try:
        connections['jira'] = await jira_connector.connect()
    except Exception as e:
        print(f"⚠️ JIRA connection failed: {e}")
        connections['jira'] = False
    
    print("🔗 Testing Tempo connection...")
    try:
        connections['tempo'] = await tempo_connector.connect()
    except Exception as e:
        print(f"⚠️ Tempo connection failed: {e}")
        connections['tempo'] = False
    
    print("🔗 Testing Confluence connection...")
    try:
        connections['confluence'] = await confluence_connector.connect()
    except Exception as e:
        print(f"⚠️ Confluence connection failed: {e}")
        connections['confluence'] = False
    
    print(f"✅ Connection Status: JIRA={connections['jira']}, Tempo={connections['tempo']}, Confluence={connections['confluence']}")
    
    # Load initial dashboard data
    try:
        await refresh_dashboard_data()
        print("📊 Initial dashboard data loaded successfully")
    except Exception as e:
        print(f"⚠️ Warning: Could not load initial data: {e}")
        # Create fallback data so the app can still start
        global dashboard_cache
        dashboard_cache = get_fallback_dashboard_data()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup connections on shutdown"""
    await jira_connector.close()
    await tempo_connector.close()
    await confluence_connector.close()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "MCP Dashboard API - Real Data Integration", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Detailed health check with MCP connection status"""
    # Test connections
    jira_status = await test_jira_connection()
    tempo_status = await test_tempo_connection()
    confluence_status = await test_confluence_connection()
    
    return {
        "status": "healthy",
        "app_name": settings.app.app_name,
        "version": "1.0.0",
        "mcp_connections": {
            "jira": jira_status,
            "tempo": tempo_status,
            "confluence": confluence_status
        },
        "config_loaded": True,
        "openai_configured": bool(settings.openai.api_key),
        "cache_status": "fresh" if cache_expiry and cache_expiry > datetime.now() else "stale"
    }

async def test_jira_connection() -> bool:
    """Test JIRA connection"""
    try:
        # Quick test - get one project
        projects = await jira_connector.fetch_all_projects()
        return len(projects) > 0
    except Exception:
        return False

async def test_tempo_connection() -> bool:
    """Test Tempo connection"""
    try:
        # Quick test - get one worklog
        await tempo_connector.connect()
        return True
    except Exception:
        return False

async def test_confluence_connection() -> bool:
    """Test Confluence connection"""
    try:
        # Quick test - get one space
        spaces = await confluence_connector.fetch_all_spaces()
        return len(spaces) > 0
    except Exception:
        return False

@app.get("/api/dashboard/executive-summary")
async def get_executive_summary():
    """Get executive dashboard summary with real MCP data"""
    global dashboard_cache, cache_expiry
    
    # Check cache first (refresh every 10 minutes)
    if cache_expiry and cache_expiry > datetime.now() and dashboard_cache:
        print("📊 Returning cached dashboard data")
        return dashboard_cache
    
    # Refresh data
    await refresh_dashboard_data()
    return dashboard_cache

async def refresh_dashboard_data():
    """Refresh dashboard data from all MCP sources"""
    global dashboard_cache, cache_expiry
    
    print("🔄 Refreshing dashboard data from MCP sources...")
    
    try:
        # Fetch data from all sources in parallel
        tasks = [
            fetch_jira_data(),
            fetch_tempo_data(),
            fetch_confluence_data()
        ]
        
        jira_data, tempo_data, confluence_data = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        if isinstance(jira_data, Exception):
            print(f"⚠️ JIRA data fetch failed: {jira_data}")
            jira_data = get_fallback_jira_data()
        
        if isinstance(tempo_data, Exception):
            print(f"⚠️ Tempo data fetch failed: {tempo_data}")
            tempo_data = get_fallback_tempo_data()
        
        if isinstance(confluence_data, Exception):
            print(f"⚠️ Confluence data fetch failed: {confluence_data}")
            confluence_data = get_fallback_confluence_data()
        
        # Combine data into dashboard format
        dashboard_cache = combine_mcp_data(jira_data, tempo_data, confluence_data)
        cache_expiry = datetime.now() + timedelta(minutes=10)
        
        print("✅ Dashboard data refreshed successfully")
        
    except Exception as e:
        print(f"❌ Failed to refresh dashboard data: {e}")
        # Use fallback data if available
        if not dashboard_cache:
            dashboard_cache = get_fallback_dashboard_data()

async def fetch_jira_data() -> Dict[str, Any]:
    """Fetch comprehensive JIRA data"""
    print("📋 Fetching JIRA data...")
    
    # Fetch projects
    projects = await jira_connector.fetch_all_projects()
    
    # Fetch tickets for each project
    all_tickets = []
    project_health = []
    
    for project in projects[:5]:  # Limit to first 5 projects for performance
        project_key = project['key']
        tickets = await jira_connector.fetch_tickets_for_project(project_key, days_back=30)
        all_tickets.extend(tickets)
        
        # Calculate project health metrics
        health_metrics = calculate_project_health(project_key, tickets)
        project_health.append(health_metrics)
    
    # Get critical tickets
    critical_tickets = await jira_connector.get_critical_tickets()
    
    return {
        'projects': projects,
        'tickets': all_tickets,
        'critical_tickets': critical_tickets,
        'project_health': project_health
    }

async def fetch_tempo_data() -> Dict[str, Any]:
    """Fetch comprehensive Tempo data"""
    print("⏱️ Fetching Tempo data...")
    
    # Fetch productivity metrics
    metrics = await tempo_connector.get_productivity_metrics(days_back=30)
    
    # Fetch recent worklogs
    worklogs = await tempo_connector.fetch_worklogs(days_back=30)
    
    # Fetch teams and accounts
    teams = await tempo_connector.fetch_teams()
    accounts = await tempo_connector.fetch_accounts()
    
    return {
        'productivity_metrics': metrics,
        'worklogs': worklogs,
        'teams': teams,
        'accounts': accounts
    }

async def fetch_confluence_data() -> Dict[str, Any]:
    """Fetch comprehensive Confluence data"""
    print("📚 Fetching Confluence data...")
    
    # Fetch spaces
    spaces = await confluence_connector.fetch_all_spaces()
    
    # Fetch recent pages from key spaces (limit for performance)
    all_pages = []
    for space in spaces[:3]:  # Limit to first 3 spaces
        pages = await confluence_connector.fetch_pages_in_space(space['key'], days_back=30)
        all_pages.extend(pages)
    
    return {
        'spaces': spaces,
        'pages': all_pages
    }

def calculate_project_health(project_key: str, tickets: List[Dict]) -> Dict[str, Any]:
    """Calculate health metrics for a project"""
    if not tickets:
        return {
            'project_key': project_key,
            'project_name': project_key,
            'health_score': 5,
            'stalled_tickets': 0,
            'overdue_tickets': 0,
            'recent_deployments': 0,
            'risk_level': 'medium'
        }
    
    total_tickets = len(tickets)
    stalled_tickets = sum(1 for t in tickets if t.get('is_stalled', False))
    overdue_tickets = sum(1 for t in tickets if t.get('is_overdue', False))
    failed_tests = sum(1 for t in tickets if t.get('level_ii_failed', False))
    
    # Calculate health score (1-10)
    health_score = 10
    health_score -= min(3, stalled_tickets * 0.5)  # Max -3 for stalled
    health_score -= min(3, overdue_tickets * 0.7)  # Max -3 for overdue
    health_score -= min(2, failed_tests * 1.0)     # Max -2 for failed tests
    health_score = max(1, min(10, round(health_score)))
    
    # Determine risk level
    if health_score >= 8:
        risk_level = 'low'
    elif health_score >= 6:
        risk_level = 'medium'
    else:
        risk_level = 'high'
    
    return {
        'project_key': project_key,
        'project_name': f"{project_key} Project",
        'health_score': health_score,
        'stalled_tickets': stalled_tickets,
        'overdue_tickets': overdue_tickets,
        'recent_deployments': 0,  # Would need deployment data
        'risk_level': risk_level
    }

def combine_mcp_data(jira_data: Dict, tempo_data: Dict, confluence_data: Dict) -> Dict[str, Any]:
    """Combine data from all MCP sources into dashboard format"""
    
    # Extract metrics from JIRA data
    total_tickets = len(jira_data.get('tickets', []))
    stalled_tickets = sum(1 for t in jira_data.get('tickets', []) if t.get('is_stalled', False))
    overdue_tickets = sum(1 for t in jira_data.get('tickets', []) if t.get('is_overdue', False))
    critical_tickets = len(jira_data.get('critical_tickets', []))
    failed_deployments = sum(1 for t in jira_data.get('tickets', []) if t.get('level_ii_failed', False))
    
    # Extract metrics from Tempo data
    tempo_metrics = tempo_data.get('productivity_metrics', {})
    total_hours = tempo_metrics.get('total_hours_logged', 0)
    unique_contributors = tempo_metrics.get('unique_contributors', 0)
    
    # Calculate team utilization (simplified)
    expected_hours_per_person = 40 * 4  # 40 hours/week * 4 weeks
    expected_total_hours = unique_contributors * expected_hours_per_person
    team_utilization = min(100, round((total_hours / max(expected_total_hours, 1)) * 100)) if expected_total_hours > 0 else 0
    
    # Calculate client satisfaction (simplified based on project health)
    project_health_scores = [p.get('health_score', 5) for p in jira_data.get('project_health', [])]
    avg_health = sum(project_health_scores) / len(project_health_scores) if project_health_scores else 5
    client_satisfaction = round(avg_health * 0.8 + 2, 1)  # Scale to 1-10
    
    # Calculate delivery risk
    risk_factors = stalled_tickets + overdue_tickets + failed_deployments
    delivery_risk = min(10, max(1, risk_factors * 0.5 + 1))
    
    # Generate trend data (simplified - last 30 days)
    trends = generate_trend_data(jira_data.get('tickets', []))
    
    return {
        "kpis": {
            "total_tickets": total_tickets,
            "stalled_tickets": stalled_tickets,
            "overdue_tickets": overdue_tickets,
            "failed_deployments": failed_deployments,
            "critical_alerts": critical_tickets,
            "client_satisfaction_score": client_satisfaction,
            "delivery_risk_score": delivery_risk,
            "team_utilization": team_utilization
        },
        "project_health": jira_data.get('project_health', []),
        "trends": trends,
        "urgent_items": {
            "critical_alerts": critical_tickets,
            "high_risk_projects": [p['project_key'] for p in jira_data.get('project_health', []) if p.get('risk_level') == 'high'],
            "overdue_tickets": overdue_tickets,
            "failed_deployments": failed_deployments
        },
        "timestamp": datetime.now().isoformat(),
        "data_sources": {
            "jira_projects": len(jira_data.get('projects', [])),
            "jira_tickets": len(jira_data.get('tickets', [])),
            "tempo_worklogs": len(tempo_data.get('worklogs', [])),
            "confluence_spaces": len(confluence_data.get('spaces', []))
        }
    }

def generate_trend_data(tickets: List[Dict]) -> List[Dict]:
    """Generate trend data from ticket information"""
    trends = []
    end_date = datetime.now().date()
    
    for i in range(30):
        date = end_date - timedelta(days=29-i)
        
        # Count tickets created/resolved on this date (simplified)
        created_count = sum(1 for t in tickets 
                          if t.get('created_date') and t['created_date'].date() == date)
        resolved_count = sum(1 for t in tickets 
                           if t.get('resolution_date') and t['resolution_date'].date() == date)
        
        trends.append({
            "date": date.isoformat(),
            "tickets_created": created_count,
            "tickets_resolved": resolved_count,
            "stalled_count": max(0, created_count - resolved_count),
            "overdue_count": 0  # Would need more complex calculation
        })
    
    return trends

def get_fallback_jira_data() -> Dict[str, Any]:
    """Provide fallback JIRA data if connection fails"""
    return {
        'projects': [{'key': 'DEMO', 'name': 'Demo Project'}],
        'tickets': [],
        'critical_tickets': [],
        'project_health': [{
            'project_key': 'DEMO',
            'project_name': 'Demo Project',
            'health_score': 5,
            'stalled_tickets': 0,
            'overdue_tickets': 0,
            'recent_deployments': 0,
            'risk_level': 'medium'
        }]
    }

def get_fallback_tempo_data() -> Dict[str, Any]:
    """Provide fallback Tempo data if connection fails"""
    return {
        'productivity_metrics': {
            'total_hours_logged': 0,
            'unique_contributors': 1
        },
        'worklogs': [],
        'teams': [],
        'accounts': []
    }

def get_fallback_confluence_data() -> Dict[str, Any]:
    """Provide fallback Confluence data if connection fails"""
    return {
        'spaces': [],
        'pages': []
    }

def get_fallback_dashboard_data() -> Dict[str, Any]:
    """Provide fallback dashboard data if all else fails"""
    return combine_mcp_data(
        get_fallback_jira_data(),
        get_fallback_tempo_data(),
        get_fallback_confluence_data()
    )

@app.get("/api/dashboard/kpis")
async def get_kpis():
    """Get KPI data"""
    summary = await get_executive_summary()
    return summary.get('kpis', {})

@app.post("/api/dashboard/refresh")
async def refresh_dashboard():
    """Refresh dashboard data from MCP sources"""
    try:
        await refresh_dashboard_data()
        return {"message": "Dashboard data refreshed successfully from MCP sources"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh data: {str(e)}")

@app.get("/api/alerts/summary")
async def get_alerts_summary():
    """Get alerts summary from dashboard data"""
    summary = await get_executive_summary()
    urgent_items = summary.get('urgent_items', {})
    
    return {
        "critical_alerts": urgent_items.get('critical_alerts', 0),
        "warning_alerts": urgent_items.get('overdue_tickets', 0),
        "info_alerts": len(urgent_items.get('high_risk_projects', [])),
        "total_alerts": urgent_items.get('critical_alerts', 0) + urgent_items.get('overdue_tickets', 0) + len(urgent_items.get('high_risk_projects', []))
    }

@app.get("/api/mcp/status")
async def get_mcp_status():
    """Get detailed MCP connector status"""
    jira_projects = []
    tempo_teams = []
    confluence_spaces = []
    
    try:
        jira_projects = await jira_connector.fetch_all_projects()
    except Exception as e:
        print(f"JIRA status check failed: {e}")
    
    try:
        tempo_teams = await tempo_connector.fetch_teams()
    except Exception as e:
        print(f"Tempo status check failed: {e}")
    
    try:
        confluence_spaces = await confluence_connector.fetch_all_spaces()
    except Exception as e:
        print(f"Confluence status check failed: {e}")
    
    return {
        "jira": {
            "connected": len(jira_projects) > 0,
            "projects_count": len(jira_projects),
            "projects": [p['key'] for p in jira_projects[:10]]  # First 10 project keys
        },
        "tempo": {
            "connected": len(tempo_teams) > 0,
            "teams_count": len(tempo_teams),
            "teams": [t['team_name'] for t in tempo_teams[:10]]  # First 10 team names
        },
        "confluence": {
            "connected": len(confluence_spaces) > 0,
            "spaces_count": len(confluence_spaces),
            "spaces": [s['key'] for s in confluence_spaces[:10]]  # First 10 space keys
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.debug,
        log_level="info"
    )