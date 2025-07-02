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

# Cache for raw MCP data (used by other endpoints)
mcp_data_cache = {
    'jira_data': None,
    'tempo_data': None, 
    'confluence_data': None
}
mcp_cache_expiry = None

# Background refresh control to prevent infinite loops
background_refresh_running = False
last_refresh_attempt = None
refresh_cooldown_minutes = 10  # Minimum time between refresh attempts

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
    global dashboard_cache, cache_expiry, background_refresh_running, last_refresh_attempt
    
    # Always return cached data if available to prevent blocking
    if dashboard_cache:
        print("📊 Returning cached dashboard data")
        # Trigger background refresh if cache is getting old AND no refresh is running
        should_refresh = (
            not cache_expiry or 
            cache_expiry < datetime.now() + timedelta(minutes=30)
        )
        
        cooldown_check = (
            not last_refresh_attempt or 
            last_refresh_attempt < datetime.now() - timedelta(minutes=refresh_cooldown_minutes)
        )
        
        if should_refresh and not background_refresh_running and cooldown_check:
            import asyncio
            asyncio.create_task(refresh_dashboard_data_background())
        return dashboard_cache
    
    # No cache available - wait for initial load only
    print("🔄 No cache available, loading initial data...")
    await refresh_dashboard_data()
    return dashboard_cache

async def refresh_dashboard_data():
    """Refresh dashboard data from all MCP sources"""
    global dashboard_cache, cache_expiry, mcp_data_cache, mcp_cache_expiry
    
    print("🔄 Refreshing dashboard data from MCP sources...")
    
    try:
        # Fetch data from all sources in parallel
        tasks = [
            fetch_jira_data(),
            asyncio.sleep(0),  # Placeholder for tempo - will fetch after JIRA
            fetch_confluence_data()
        ]
        
        jira_data, tempo_placeholder, confluence_data = await asyncio.gather(
            fetch_jira_data(),
            asyncio.sleep(0),  # Placeholder to maintain structure
            fetch_confluence_data(),
            return_exceptions=True
        )
        
        # Now fetch Tempo data with JIRA enrichment
        tempo_data = await fetch_tempo_data(jira_data if not isinstance(jira_data, Exception) else None)
        
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
        
        # Store raw MCP data in cache for other endpoints
        mcp_data_cache['jira_data'] = jira_data
        mcp_data_cache['tempo_data'] = tempo_data
        mcp_data_cache['confluence_data'] = confluence_data
        mcp_cache_expiry = datetime.now() + timedelta(hours=2)  # Increased cache time for stability
        
        # Combine data into dashboard format
        dashboard_cache = combine_mcp_data(jira_data, tempo_data, confluence_data)
        cache_expiry = datetime.now() + timedelta(hours=2)  # Increased cache time for stability
        
        print("✅ Dashboard data refreshed successfully")
        
    except Exception as e:
        print(f"❌ Failed to refresh dashboard data: {e}")
        # Use fallback data if available
        if not dashboard_cache:
            dashboard_cache = get_fallback_dashboard_data()

async def refresh_dashboard_data_background():
    """Background refresh that doesn't block API responses"""
    global background_refresh_running, last_refresh_attempt
    
    if background_refresh_running:
        print("🔄 Background refresh already running, skipping...")
        return
    
    try:
        background_refresh_running = True
        last_refresh_attempt = datetime.now()
        print("🔄 Starting background data refresh...")
        await refresh_dashboard_data()
        print("✅ Background refresh completed successfully")
    except Exception as e:
        print(f"🔄 Background refresh failed (non-blocking): {e}")
        # Don't crash the app, just log the error
    finally:
        background_refresh_running = False

async def fetch_jira_data() -> Dict[str, Any]:
    """Fetch comprehensive JIRA data"""
    print("📋 Fetching JIRA data...")
    
    # Fetch projects
    projects = await jira_connector.fetch_all_projects()
    
    # Fetch tickets for each project
    all_tickets = []
    project_health = []
    
    for project in projects:  # Process all projects for complete data
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

async def fetch_tempo_data(jira_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Fetch comprehensive Tempo data with JIRA enrichment"""
    print("⏱️ Fetching Tempo data...")
    
    # Create JIRA mappings if JIRA data is available
    jira_mappings = None
    if jira_data:
        tickets = jira_data.get('tickets', [])
        # Create issue ID to ticket key mapping
        issue_mapping = jira_connector.create_issue_id_to_key_mapping(tickets)
        # Create account ID to display name mapping
        user_mapping = jira_connector.create_account_id_to_name_mapping(tickets)
        
        jira_mappings = {
            'issue_mapping': issue_mapping,
            'user_mapping': user_mapping
        }
        
        print(f"📊 Created JIRA mappings: {len(issue_mapping)} issues, {len(user_mapping)} users")
    
    # Fetch productivity metrics
    metrics = await tempo_connector.get_productivity_metrics(days_back=30)
    
    # Fetch recent worklogs with JIRA enrichment
    worklogs = await tempo_connector.fetch_worklogs(days_back=30, jira_mappings=jira_mappings)
    
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
    
    # Extract deployment records from all spaces
    print("📋 Extracting deployment records...")
    deployment_records = await confluence_connector.extract_deployment_records()
    
    return {
        'spaces': spaces,
        'pages': all_pages,
        'deployments': deployment_records
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
    
    # Include all tickets in total count, but exclude Done tickets from problem calculations
    done_statuses = ['done', 'closed', 'resolved', 'completed']
    active_tickets = [t for t in tickets if t.get('status', '').lower() not in done_statuses]
    
    total_tickets = len(tickets)  # Include ALL tickets in total count
    stalled_tickets = sum(1 for t in active_tickets if t.get('is_stalled', False))  # Exclude done from stalled
    overdue_tickets = sum(1 for t in active_tickets if t.get('is_overdue', False))  # Exclude done from overdue
    failed_tests = sum(1 for t in active_tickets if t.get('level_ii_failed', False))  # Exclude done from failed tests
    
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
    
    # Extract metrics from JIRA data - include Done tickets in totals but exclude from problems
    all_tickets = jira_data.get('tickets', [])
    done_statuses = ['done', 'closed', 'resolved', 'completed']
    active_tickets = [t for t in all_tickets if t.get('status', '').lower() not in done_statuses]
    
    total_tickets = len(all_tickets)  # Include ALL tickets in total count
    stalled_tickets = sum(1 for t in active_tickets if t.get('is_stalled', False))  # Exclude done from stalled
    overdue_tickets = sum(1 for t in active_tickets if t.get('is_overdue', False))  # Exclude done from overdue
    
    # Critical tickets should also exclude done tickets
    all_critical = jira_data.get('critical_tickets', [])
    critical_tickets = len([t for t in all_critical if t.get('status', '').lower() not in done_statuses])
    
    # Calculate failed deployments from both JIRA and Confluence data - exclude done tickets
    jira_failed_tests = sum(1 for t in active_tickets if t.get('level_ii_failed', False))
    
    # Extract failed deployments from Confluence deployment records
    confluence_failed_deployments = 0
    for deployment_record in confluence_data.get('deployments', []):
        for entry in deployment_record.get('entries', []):
            for case in entry.get('cases', []):
                if case.get('has_failures', False) or 'failed' in case.get('status', '').lower():
                    confluence_failed_deployments += 1
    
    failed_deployments = jira_failed_tests + confluence_failed_deployments
    
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
    
    # Sort projects by risk (high risk first, then by stalled tickets descending)
    project_health = jira_data.get('project_health', [])
    risk_order = {'high': 0, 'medium': 1, 'low': 2}
    project_health.sort(key=lambda p: (
        risk_order.get(p.get('risk_level', 'medium'), 1),  # Risk level priority
        -p.get('stalled_tickets', 0),  # Stalled tickets (descending)
        -p.get('overdue_tickets', 0)   # Overdue tickets (descending)
    ))
    
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
        "project_health": project_health,
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

# JIRA Endpoints
@app.get("/api/jira/tickets")
async def get_jira_tickets(project: str = None, status: str = None, assignee: str = None, priority: str = None, 
                          stalled_only: bool = False, overdue_only: bool = False, failed_testing_only: bool = False,
                          exclude_done: bool = False, limit: int = 50, offset: int = 0):
    """Get JIRA tickets with optional filtering"""
    try:
        # Use cached MCP data if available
        global mcp_data_cache, mcp_cache_expiry
        
        # Always use cached data if available, never block for refresh
        if mcp_data_cache.get('jira_data'):
            print("📊 Using cached JIRA data for tickets")
            jira_data = mcp_data_cache['jira_data']
            all_tickets = jira_data.get('tickets', [])
            
            if project:
                # Filter by specific project
                tickets = [t for t in all_tickets if t.get('project_key') == project or t.get('key', '').startswith(f"{project}-")]
            else:
                # Return all tickets from cache
                tickets = all_tickets
                
            # Trigger background refresh if cache is getting stale
            if not mcp_cache_expiry or mcp_cache_expiry < datetime.now() + timedelta(minutes=30):
                import asyncio
                asyncio.create_task(refresh_dashboard_data_background())
        else:
            # No cache available - try direct JIRA fetch but keep it fast
            print("⚠️ No cache available, fetching limited JIRA data...")
            if project:
                tickets = await jira_connector.fetch_tickets_for_project(project, days_back=30)
            else:
                # For efficiency, just get PIH project if no cache
                tickets = await jira_connector.fetch_tickets_for_project('PIH', days_back=30)
        
        # Exclude "Done" tickets by default (but keep "Ready for Prod")
        if exclude_done:
            done_statuses = ['done', 'closed', 'resolved', 'completed']
            filtered_tickets = [t for t in tickets if t.get('status', '').lower() not in done_statuses]
        else:
            filtered_tickets = tickets
        
        # Apply status filter
        if status:
            filtered_tickets = [t for t in filtered_tickets if t.get('status', '').lower() == status.lower()]
        
        # Apply assignee filter
        if assignee:
            filtered_tickets = [t for t in filtered_tickets if assignee.lower() in t.get('assignee', '').lower()]
        
        # Apply priority filter
        if priority:
            filtered_tickets = [t for t in filtered_tickets if t.get('priority', '').lower() == priority.lower()]
        
        # Apply stalled filter - exclude done tickets from stalled calculation
        if stalled_only:
            stalled_tickets = []
            for ticket in filtered_tickets:
                ticket_status = ticket.get('status', '').lower()
                # Don't consider done tickets as stalled
                if ticket_status in ['done', 'closed', 'resolved', 'completed']:
                    continue
                # Consider tickets stalled if they haven't been updated in 7+ days and aren't ready for prod
                if ticket.get('is_stalled', False) or (
                    ticket_status not in ['ready for prod', 'ready for production'] and
                    ticket.get('days_since_update', 0) >= 7
                ):
                    stalled_tickets.append(ticket)
            filtered_tickets = stalled_tickets
        
        # Apply overdue filter
        if overdue_only:
            filtered_tickets = [t for t in filtered_tickets if t.get('is_overdue', False)]
        
        # Apply failed testing filter - check both JIRA flags and confluence deployment failures
        if failed_testing_only:
            failed_tickets = []
            for ticket in filtered_tickets:
                # Check JIRA level II testing failed flag
                if ticket.get('level_ii_failed', False):
                    failed_tickets.append(ticket)
                    continue
                
                # Check if ticket has test-related failures 
                # Prioritize status-based matching for accuracy
                status = (ticket.get('status') or '').lower()
                
                # Primary: Check status for test failure indicators
                status_failure_patterns = [
                    'test failed', 'testing failed', 'qa failed', 'level ii test failed',
                    'failed testing', 'failed qa', 'test failure', 'testing failure', 'qa failure'
                ]
                
                if any(pattern in status for pattern in status_failure_patterns):
                    failed_tickets.append(ticket)
                    continue
                
                # Secondary: Check summary for explicit test failure mentions (more conservative)
                summary = (ticket.get('summary') or '').lower()
                summary_failure_patterns = [
                    'test failed', 'testing failed', 'qa failed', 'test failure', 'testing failure'
                ]
                
                if any(pattern in summary for pattern in summary_failure_patterns):
                    failed_tickets.append(ticket)
            filtered_tickets = failed_tickets
        
        # Format response to match frontend expectations
        total_count = len(filtered_tickets)
        paginated_tickets = filtered_tickets[offset:offset + limit]
        
        return {
            "tickets": paginated_tickets,
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "filters_applied": {
                "project": project,
                "status": status,
                "assignee": assignee,
                "priority": priority,
                "stalled_only": stalled_only,
                "overdue_only": overdue_only,
                "failed_testing_only": failed_testing_only,
                "exclude_done": exclude_done
            },
            "summary": {
                "total_tickets": total_count,
                "stalled_count": len([t for t in filtered_tickets if t.get('is_stalled', False)]),
                "overdue_count": len([t for t in filtered_tickets if t.get('is_overdue', False)]),
                "failed_testing_count": len([t for t in filtered_tickets if t.get('level_ii_failed', False)])
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tickets: {str(e)}")

@app.get("/api/jira/search")
async def search_jira_tickets(query: str, limit: int = 25):
    """Search JIRA tickets by text"""
    try:
        # For demo purposes, search in PIH project for fast response
        all_tickets = await jira_connector.fetch_tickets_for_project('PIH', days_back=30)
        
        # Filter by query in title, description, or key
        query_lower = query.lower()
        matching_tickets = []
        for ticket in all_tickets:
            if (query_lower in ticket.get('title', '').lower() or 
                query_lower in ticket.get('summary', '').lower() or
                query_lower in ticket.get('description', '').lower() or
                query_lower in ticket.get('key', '').lower() or
                query_lower in ticket.get('ticket_key', '').lower()):
                matching_tickets.append(ticket)
        
        return {
            "results": matching_tickets[:limit],
            "tickets": matching_tickets[:limit],  # Also provide in expected format
            "query": query,
            "total_matches": len(matching_tickets)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/api/jira/projects")
async def get_jira_projects():
    """Get all JIRA projects with metadata"""
    try:
        # Use cached MCP data if available
        global mcp_data_cache
        
        if mcp_data_cache.get('jira_data'):
            print("📊 Using cached JIRA data for projects")
            jira_data = mcp_data_cache['jira_data']
            projects = jira_data.get('projects', [])
        else:
            # No cache available - fetch directly from JIRA
            print("⚠️ No cache available, fetching projects from JIRA...")
            projects = await jira_connector.fetch_all_projects()
        
        # Transform projects data for frontend consumption
        project_metadata = []
        for project in projects:
            project_info = {
                'key': project.get('key', ''),
                'name': project.get('name', project.get('key', '')),
                'description': project.get('description', ''),
                'lead': project.get('lead', ''),
                'project_type': project.get('project_type', 'unknown')
            }
            project_metadata.append(project_info)
        
        return {
            "projects": project_metadata,
            "total_count": len(project_metadata)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch projects: {str(e)}")

# Alerts Endpoints  
@app.get("/api/alerts/")
async def get_alerts(severity: str = None, status: str = None, alert_type: str = None, 
                     days_back: int = 7, limit: int = 50, offset: int = 0):
    """Get all alerts with filtering and pagination"""
    try:
        summary = await get_executive_summary()
        urgent_items = summary.get('urgent_items', {})
        kpis = summary.get('kpis', {})
        
        alerts = []
        alert_id = 1
        current_time = datetime.now()
        
        # Create alerts from urgent items with full Alert schema
        if urgent_items.get('critical_alerts', 0) > 0:
            alerts.append({
                "id": str(alert_id),
                "alert_type": "critical_tickets",
                "severity": "critical",
                "status": "active",
                "title": f"{urgent_items['critical_alerts']} Critical Tickets Require Attention",
                "description": "High priority tickets need immediate review and action",
                "recommendation": "Review critical tickets and assign resources immediately",
                "jira_ticket_key": None,
                "project_key": None,
                "assignee": "Project Manager",
                "client": "Multiple Clients",
                "context_data": {"count": urgent_items['critical_alerts']},
                "first_detected": current_time.isoformat(),
                "last_updated": current_time.isoformat(),
                "acknowledged_at": None,
                "acknowledged_by": None,
                "resolved_at": None,
                "resolved_by": None,
                "auto_resolve": False
            })
            alert_id += 1
        
        if urgent_items.get('overdue_tickets', 0) > 0:
            alerts.append({
                "id": str(alert_id),
                "alert_type": "overdue_tickets",
                "severity": "high",
                "status": "active",
                "title": f"{urgent_items['overdue_tickets']} Overdue Tickets",
                "description": "Tickets have passed their due date and require immediate attention",
                "recommendation": "Review overdue tickets and update delivery timelines",
                "jira_ticket_key": None,
                "project_key": None,
                "assignee": "Team Lead",
                "client": "Multiple Clients",
                "context_data": {"count": urgent_items['overdue_tickets']},
                "first_detected": current_time.isoformat(),
                "last_updated": current_time.isoformat(),
                "acknowledged_at": None,
                "acknowledged_by": None,
                "resolved_at": None,
                "resolved_by": None,
                "auto_resolve": False
            })
            alert_id += 1
        
        if urgent_items.get('failed_deployments', 0) > 0:
            alerts.append({
                "id": str(alert_id),
                "alert_type": "failed_deployments",
                "severity": "critical",
                "status": "active",
                "title": f"{urgent_items['failed_deployments']} Failed Deployments",
                "description": "Recent deployments have failed and need investigation",
                "recommendation": "Check deployment logs and rollback if necessary",
                "jira_ticket_key": None,
                "project_key": None,
                "assignee": "DevOps Team",
                "client": "Multiple Clients",
                "context_data": {"count": urgent_items['failed_deployments']},
                "first_detected": current_time.isoformat(),
                "last_updated": current_time.isoformat(),
                "acknowledged_at": None,
                "acknowledged_by": None,
                "resolved_at": None,
                "resolved_by": None,
                "auto_resolve": False
            })
            alert_id += 1
        
        # Add stalled tickets alert
        if kpis.get('stalled_tickets', 0) > 5:
            alerts.append({
                "id": str(alert_id),
                "alert_type": "stalled_tickets",
                "severity": "medium",
                "status": "active",
                "title": f"{kpis['stalled_tickets']} Stalled Tickets",
                "description": "Multiple tickets have been stalled for extended periods",
                "recommendation": "Review stalled tickets and identify blockers",
                "jira_ticket_key": None,
                "project_key": None,
                "assignee": "Project Manager",
                "client": "Multiple Clients",
                "context_data": {"count": kpis['stalled_tickets']},
                "first_detected": current_time.isoformat(),
                "last_updated": current_time.isoformat(),
                "acknowledged_at": None,
                "acknowledged_by": None,
                "resolved_at": None,
                "resolved_by": None,
                "auto_resolve": False
            })
        
        # Apply filters
        filtered_alerts = alerts
        if severity:
            filtered_alerts = [a for a in filtered_alerts if a['severity'] == severity]
        if status:
            filtered_alerts = [a for a in filtered_alerts if a['status'] == status]
        if alert_type:
            filtered_alerts = [a for a in filtered_alerts if a['alert_type'] == alert_type]
        
        # Pagination
        total_count = len(filtered_alerts)
        paginated_alerts = filtered_alerts[offset:offset + limit]
        
        # Calculate summary statistics
        critical_count = len([a for a in alerts if a['severity'] == 'critical'])
        high_count = len([a for a in alerts if a['severity'] == 'high'])
        unresolved_count = len([a for a in alerts if a['status'] == 'active'])
        
        return {
            "alerts": paginated_alerts,
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "summary": {
                "total_alerts": len(alerts),
                "critical_alerts": critical_count,
                "high_priority_alerts": high_count,
                "unresolved_alerts": unresolved_count,
                "recent_alerts": len(alerts),  # All are recent
                "resolution_rate": 0.0  # No resolved alerts yet
            },
            "filters_applied": {
                "severity": severity,
                "status": status,
                "alert_type": alert_type,
                "days_back": days_back
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch alerts: {str(e)}")

@app.get("/api/alerts/active")
async def get_active_alerts():
    """Get only active alerts"""
    alerts = await get_alerts()
    active_alerts = [a for a in alerts["alerts"] if a["status"] == "active"]
    return {"alerts": active_alerts}

@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int):
    """Acknowledge an alert (placeholder implementation)"""
    return {"message": f"Alert {alert_id} acknowledged", "acknowledged_at": datetime.now().isoformat()}

# Analytics Endpoints
@app.get("/api/analytics/business-metrics")
async def get_business_metrics():
    """Get business intelligence metrics"""
    try:
        summary = await get_executive_summary()
        kpis = summary.get('kpis', {})
        
        # Use cached JIRA data instead of making new API call
        project_distribution = {}
        if mcp_data_cache.get('jira_data'):
            tickets = mcp_data_cache['jira_data'].get('tickets', [])
            for ticket in tickets:
                if ticket.get('is_stalled', False):
                    project_key = ticket.get('project_key', 'Unknown')
                    project_distribution[project_key] = project_distribution.get(project_key, 0) + 1
        
        # Calculate risk scores on 1-10 scale (higher = worse)
        total_tickets = max(1, kpis.get('total_tickets', 1))
        stalled_tickets = kpis.get('stalled_tickets', 0)
        overdue_tickets = kpis.get('overdue_tickets', 0)
        level_ii_failed = kpis.get('level_ii_failed_tickets', 0)
        failed_deployments = kpis.get('failed_deployments', 0)
        
        # Delivery risk: stalled + overdue + level II failures (all cause delivery delays)
        delivery_issues = stalled_tickets + overdue_tickets + level_ii_failed
        delivery_risk_score = min(10, round((delivery_issues / total_tickets) * 10, 1))
        
        # Quality risk: deployment failures + level II failures (both indicate quality issues)
        # Level II failures indicate poor development quality, deployment failures indicate production issues
        quality_issues_score = (failed_deployments * 2.5) + (level_ii_failed / total_tickets * 5)
        quality_risk_score = min(10, round(quality_issues_score, 1))
        
        # Utilization score: optimal is 80-100%, higher is better on 1-10 scale
        team_utilization = kpis.get('team_utilization', 80)
        if 80 <= team_utilization <= 100:
            utilization_score = 10 - abs(90 - team_utilization) / 10  # Optimal around 90%
        else:
            utilization_score = max(1, 10 - abs(90 - team_utilization) / 5)  # Penalize deviation
        utilization_score = round(utilization_score, 1)
        
        return {
            "delivery_metrics": {
                "delivery_risk_score": delivery_risk_score,  # Scale 1-10: higher = worse delivery risk
                "total_tickets": kpis.get('total_tickets', 0),
                "completed_tickets": max(0, kpis.get('total_tickets', 0) - delivery_issues),
                "stalled_tickets": stalled_tickets,
                "overdue_tickets": overdue_tickets,
                "level_ii_failed_tickets": level_ii_failed
            },
            "quality_metrics": {
                "quality_risk_score": quality_risk_score,  # Scale 1-10: higher = worse quality risk
                "failed_deployments": failed_deployments,
                "level_ii_failed_tickets": level_ii_failed,
                "deployment_success_rate": max(0, round(10 - quality_risk_score, 1))
            },
            "resource_metrics": {
                "utilization_score": utilization_score,  # Scale 1-10: higher = better utilization
                "utilization": round(team_utilization, 1),
                "productivity_score": utilization_score,  # Scale 1-10: higher = better productivity
                "project_distribution": project_distribution
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch business metrics: {str(e)}")

@app.get("/api/analytics/client-impact")
async def get_client_impact():
    """Get client impact analysis"""
    try:
        summary = await get_executive_summary()
        project_health = summary.get('project_health', [])
        
        # Group by risk level for client impact
        high_risk = [p for p in project_health if p.get('risk_level') == 'high']
        medium_risk = [p for p in project_health if p.get('risk_level') == 'medium']
        
        # Create client data array for the table
        clients = []
        for project in project_health:
            client_data = {
                "client_name": project.get('project_key', 'Unknown'),
                "overdue_tickets": project.get('overdue_tickets', 0),
                "failed_deployments": project.get('failed_deployments', 0),
                "overall_risk": project.get('risk_level', 'low')
            }
            clients.append(client_data)
        
        return {
            "high_risk_clients": len(high_risk),
            "medium_risk_clients": len(medium_risk),
            "at_risk_projects": [p['project_key'] for p in high_risk],
            "total_affected_tickets": sum(p.get('stalled_tickets', 0) + p.get('overdue_tickets', 0) for p in high_risk),
            "clients": clients
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch client impact: {str(e)}")

@app.get("/api/analytics/team-performance")
async def get_team_performance():
    """Get team performance metrics"""
    try:
        # Use cached Tempo data instead of making new API call
        worklogs = []
        if mcp_data_cache.get('tempo_data'):
            worklogs = mcp_data_cache['tempo_data'].get('worklogs', [])
        
        # Calculate individual team member performance
        user_performance = {}
        for log in worklogs:
            user_id = log.get('author_account_id')
            if user_id:
                # Use display name if available, otherwise use account ID as fallback
                display_name = log.get('author_display_name') or user_id.split(':')[-1][:8]  # Use last part of account ID
                
                if user_id not in user_performance:
                    user_performance[user_id] = {
                        "team_member": display_name,
                        "hours_logged": 0,
                        "tickets_worked": set(),
                        "projects_worked": set()
                    }
                user_performance[user_id]["hours_logged"] += log.get('time_spent_hours', 0)
                if log.get('jira_ticket_key'):
                    user_performance[user_id]["tickets_worked"].add(log.get('jira_ticket_key'))
                    # Extract project from ticket key
                    project_key = log.get('jira_ticket_key', '').split('-')[0]
                    if project_key:
                        user_performance[user_id]["projects_worked"].add(project_key)
        
        # Convert to performance scores (1-10 scale) with variation
        team_performance = []
        total_performance = 0
        members_needing_support = 0
        
        for user_data in user_performance.values():
            hours = user_data["hours_logged"]
            tickets = len(user_data["tickets_worked"])
            projects = len(user_data["projects_worked"])
            
            # Performance scoring on 1-10 scale with different factors for variation
            # Hours component (40% weight): based on expected 40 hours/month
            hours_component = min(10, (hours / 40) * 10) * 0.4
            
            # Ticket variety component (40% weight): based on expected 10 tickets/month
            ticket_component = min(10, (tickets / 10) * 10) * 0.4
            
            # Project diversity component (20% weight): bonus for working on multiple projects
            project_component = min(10, projects * 2) * 0.2
            
            performance_score = max(1, hours_component + ticket_component + project_component)
            
            if performance_score < 5:
                members_needing_support += 1
            
            team_performance.append({
                "team_member": user_data["team_member"],
                "performance_score": round(performance_score, 1),
                "hours_logged": round(hours, 1),
                "tickets_count": tickets
            })
            total_performance += performance_score
        
        avg_performance = total_performance / max(1, len(team_performance))
        
        return {
            "team_performance": sorted(team_performance, key=lambda x: x["performance_score"], reverse=True),
            "team_members_analyzed": len(team_performance),
            "summary": {
                "members_needing_support": members_needing_support,
                "average_performance_score": round(avg_performance, 1),
                "top_performer": team_performance[0]["team_member"] if team_performance else "N/A"
            },
            "recommendations": [
                f"Analyzed {len(team_performance)} team members",
                f"Average performance score: {round(avg_performance, 1)}/10",
                f"{members_needing_support} members may need additional support",
                "Consider workload redistribution for optimal performance"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch team performance: {str(e)}")

# Confluence/Deployments Endpoints
@app.get("/api/confluence/deployments")
async def get_deployments(days_back: int = 30, failed_only: bool = False):
    """Get deployment records from Confluence"""
    try:
        # Use cached Confluence data instead of making new API call
        print("📊 Using cached Confluence data for deployments")
        deployments = []
        if mcp_data_cache.get('confluence_data'):
            deployments = mcp_data_cache['confluence_data'].get('deployment_records', [])
        else:
            print("📚 No cached Confluence data, fetching from API...")
            confluence_data = await fetch_confluence_data()
            deployments = confluence_data.get('deployments', [])
        
        # Process deployment data for API response - with frontend format
        processed_deployments = []
        
        # If no real deployments found, create sample data for demo
        if not deployments:
            from datetime import timedelta
            current_date = datetime.now()
            
            # Create sample deployment data
            sample_deployments = [
                {
                    "page_id": "deploy_001",
                    "deployment_date": (current_date - timedelta(days=2)).isoformat(),
                    "cases": ["PIH-233", "PIH-225", "AGP-102"],
                    "has_failures": True,
                    "failure_details": [{"case": "PIH-233", "error": "Certificate rendering issue"}],
                    "deployment_status": "Failed",
                    "client_project": "PIH Project",
                    "success_rate": 66.7,
                    "ai_summary": "1 out of 3 cases failed due to certificate rendering",
                    "case_count": 3,
                    "failure_count": 1
                },
                {
                    "page_id": "deploy_002", 
                    "deployment_date": (current_date - timedelta(days=5)).isoformat(),
                    "cases": ["AGP-98", "AGP-99"],
                    "has_failures": False,
                    "failure_details": [],
                    "deployment_status": "Success",
                    "client_project": "AGP Project",
                    "success_rate": 100.0,
                    "ai_summary": "All cases deployed successfully",
                    "case_count": 2,
                    "failure_count": 0
                },
                {
                    "page_id": "deploy_003",
                    "deployment_date": (current_date - timedelta(days=7)).isoformat(), 
                    "cases": ["AREN-45", "AREN-46", "AREN-47", "AREN-48"],
                    "has_failures": False,
                    "failure_details": [],
                    "deployment_status": "Success",
                    "client_project": "AREN Project",
                    "success_rate": 100.0,
                    "ai_summary": "Smooth deployment of 4 cases",
                    "case_count": 4,
                    "failure_count": 0
                }
            ]
            processed_deployments = sample_deployments
        else:
            # Process real deployment data
            for record in deployments:
                for entry in record.get('entries', []):
                    cases = [case.get('jira_key', '') for case in entry.get('cases', [])]
                    failed_cases = [case for case in entry.get('cases', []) if case.get('has_failures', False)]
                    
                    processed_deployments.append({
                        "page_id": record.get('id', 'unknown'),
                        "deployment_date": entry.get('date', datetime.now().isoformat()),
                        "cases": cases,
                        "has_failures": len(failed_cases) > 0,
                        "failure_details": failed_cases,
                        "deployment_status": "Failed" if failed_cases else "Success",
                        "client_project": record.get('title', 'Unknown Project'),
                        "success_rate": round(((len(cases) - len(failed_cases)) / max(1, len(cases))) * 100, 1),
                        "ai_summary": f"{len(failed_cases)} failures out of {len(cases)} cases" if failed_cases else f"All {len(cases)} cases successful",
                        "case_count": len(cases),
                        "failure_count": len(failed_cases)
                    })
        
        # Apply filters
        if failed_only:
            processed_deployments = [d for d in processed_deployments if d['has_failures']]
        
        # Filter by days_back
        cutoff_date = datetime.now() - timedelta(days=days_back)
        filtered_deployments = []
        for deployment in processed_deployments:
            try:
                deploy_date = datetime.fromisoformat(deployment['deployment_date'].replace('Z', '+00:00'))
                if deploy_date >= cutoff_date:
                    filtered_deployments.append(deployment)
            except:
                # Include if date parsing fails
                filtered_deployments.append(deployment)
        
        total_count = len(filtered_deployments)
        failed_count = sum(1 for d in filtered_deployments if d['has_failures'])
        success_rate = round(((total_count - failed_count) / max(1, total_count)) * 100, 1)
        
        return {
            "deployments": filtered_deployments,
            "pagination": {
                "total_count": total_count,
                "limit": 100,
                "offset": 0,
                "has_more": False
            },
            "summary": {
                "total_deployments": total_count,
                "failed_deployments": failed_count,
                "success_rate": success_rate
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch deployments: {str(e)}")

@app.get("/api/confluence/deployments/analysis")
async def get_deployment_analysis():
    """Get deployment success/failure analysis"""
    try:
        deployments = await get_deployments()
        deployment_list = deployments["deployments"]
        
        total = len(deployment_list)
        failed = deployments["summary"]["failed_deployments"]
        success_rate = round(((total - failed) / max(1, total)) * 100, 1)
        
        return {
            "total_deployments": total,
            "successful_deployments": total - failed,
            "failed_deployments": failed,
            "success_rate_percentage": success_rate,
            "recent_failures": [d for d in deployment_list if d['has_failures']][:5]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze deployments: {str(e)}")

# Tempo/Time Tracking Endpoints
@app.get("/api/tempo/worklogs")
async def get_tempo_worklogs(days_back: int = 30, author: str = "", project: str = ""):
    """Get Tempo worklogs"""
    try:
        # Use cached Tempo data instead of making new API call
        print("📊 Using cached Tempo data for worklogs")
        worklogs = []
        if mcp_data_cache.get('tempo_data'):
            worklogs = mcp_data_cache['tempo_data'].get('worklogs', [])
        else:
            print("⏱️ No cached Tempo data, fetching from API...")
            worklogs = await tempo_connector.fetch_worklogs(days_back=days_back)
        
        # Apply filters
        filtered_worklogs = worklogs
        if author:
            filtered_worklogs = [w for w in filtered_worklogs if author.lower() in (w.get('author_display_name', '') or '').lower()]
        if project:
            filtered_worklogs = [w for w in filtered_worklogs if project.upper() in (w.get('jira_ticket_key', '') or '').upper()]
        
        # Calculate summary data
        total_hours = sum(log.get('time_spent_hours', 0) for log in filtered_worklogs)
        unique_contributors = len(set(log.get('author_account_id') for log in filtered_worklogs if log.get('author_account_id')))
        
        return {
            "worklogs": filtered_worklogs,
            "summary": {
                "total_hours_logged": round(total_hours, 1),
                "unique_contributors": unique_contributors,
                "total_entries": len(filtered_worklogs),
                "date_range_days": days_back
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch worklogs: {str(e)}")

@app.get("/api/tempo/utilization-report")
async def get_utilization_report(days_back: int = 30):
    """Get team utilization report"""
    try:
        # Use cached Tempo data instead of making new API call
        print("📊 Using cached Tempo data for utilization report")
        worklogs = []
        if mcp_data_cache.get('tempo_data'):
            worklogs = mcp_data_cache['tempo_data'].get('worklogs', [])
        else:
            print("⏱️ No cached Tempo data, fetching from API...")
            jira_data = mcp_data_cache.get('jira_data') if mcp_data_cache else None
            tempo_data = await fetch_tempo_data(jira_data)
            worklogs = tempo_data.get('worklogs', [])
        
        # Calculate utilization by user
        user_hours = {}
        user_names = {}
        for log in worklogs:
            user_id = log.get('author_account_id')
            if user_id:
                user_hours[user_id] = user_hours.get(user_id, 0) + log.get('time_spent_hours', 0)
                if log.get('author_display_name'):
                    user_names[user_id] = log.get('author_display_name')
        
        # Calculate utilization percentages (assuming 40 hours/week standard)
        expected_hours_per_week = 40
        weeks_in_period = days_back / 7
        expected_total_hours = expected_hours_per_week * weeks_in_period
        
        utilization_by_user = {}
        total_utilization = 0
        billable_hours = 0
        
        for user_id, hours in user_hours.items():
            utilization_pct = (hours / expected_total_hours) * 100
            utilization_by_user[user_names.get(user_id, user_id)] = {
                "utilization_percentage": round(utilization_pct, 1),
                "hours_logged": round(hours, 1),
                "expected_hours": round(expected_total_hours, 1)
            }
            total_utilization += utilization_pct
            billable_hours += hours
        
        avg_utilization = total_utilization / max(1, len(user_hours))
        
        # Count utilization categories
        underutilized = sum(1 for data in utilization_by_user.values() if data["utilization_percentage"] < 80)
        optimal = sum(1 for data in utilization_by_user.values() if 80 <= data["utilization_percentage"] <= 110)
        overutilized = sum(1 for data in utilization_by_user.values() if data["utilization_percentage"] > 110)
        
        return {
            "utilization_by_user": utilization_by_user,
            "team_summary": {
                "average_utilization": round(avg_utilization, 1),
                "total_billable_hours": round(billable_hours, 1),
                "total_members": len(user_hours),
                "underutilized_members": underutilized,
                "optimal_utilization_members": optimal,
                "overutilized_members": overutilized
            },
            "recommendations": [
                f"Total team members analyzed: {len(user_hours)}",
                f"Average utilization: {round(avg_utilization, 1)}%",
                f"Members under-utilized (<80%): {underutilized}",
                f"Members optimally utilized (80-110%): {optimal}",
                f"Members over-utilized (>110%): {overutilized}"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate utilization report: {str(e)}")

@app.get("/api/tempo/authors")
async def get_tempo_authors():
    """Get list of authors for dropdown filters"""
    try:
        # Use cached Tempo data, fallback to fresh data
        worklogs = []
        if mcp_data_cache.get('tempo_data'):
            worklogs = mcp_data_cache['tempo_data'].get('worklogs', [])
            print(f"📊 Using cached Tempo data for authors, found {len(worklogs)} worklogs")
        else:
            print("⏱️ No cached Tempo data, fetching fresh worklogs for authors...")
            worklogs = await tempo_connector.fetch_worklogs(days_back=30)
        
        author_set = set()
        for log in worklogs:
            if log.get('author_display_name'):
                author_set.add(log.get('author_display_name'))
        authors = sorted(list(author_set))
        
        print(f"📊 Found {len(authors)} unique authors: {authors[:5]}...")
        return {"authors": authors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch authors: {str(e)}")

@app.get("/api/tempo/projects")
async def get_tempo_projects():
    """Get list of projects for dropdown filters"""
    try:
        # Use cached Tempo data, fallback to fresh data
        worklogs = []
        if mcp_data_cache.get('tempo_data'):
            worklogs = mcp_data_cache['tempo_data'].get('worklogs', [])
            print(f"📊 Using cached Tempo data for projects, found {len(worklogs)} worklogs")
        else:
            print("⏱️ No cached Tempo data, fetching fresh worklogs for projects...")
            worklogs = await tempo_connector.fetch_worklogs(days_back=30)
        
        project_set = set()
        for log in worklogs:
            if log.get('jira_ticket_key'):
                project_key = log.get('jira_ticket_key', '').split('-')[0]
                if project_key:
                    project_set.add(project_key)
        projects = sorted(list(project_set))
        
        print(f"📊 Found {len(projects)} unique projects: {projects[:10]}...")
        return {"projects": projects}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch projects: {str(e)}")

@app.get("/api/tempo/statistics")
async def get_tempo_statistics():
    """Get Tempo statistics"""
    try:
        # Use cached Tempo data instead of making new API call
        print("📊 Using cached Tempo data for statistics")
        worklogs = []
        teams = []
        if mcp_data_cache.get('tempo_data'):
            worklogs = mcp_data_cache['tempo_data'].get('worklogs', [])
            teams = mcp_data_cache['tempo_data'].get('teams', [])
        else:
            print("⏱️ No cached Tempo data, fetching from API...")
            jira_data = mcp_data_cache.get('jira_data') if mcp_data_cache else None
            tempo_data = await fetch_tempo_data(jira_data)
            worklogs = tempo_data.get('worklogs', [])
            teams = tempo_data.get('teams', [])
        
        # Calculate statistics from the Tempo connector data
        total_hours = sum(log.get('time_spent_hours', 0) for log in worklogs)
        unique_users = len(set(log.get('author_account_id', '') for log in worklogs if log.get('author_account_id')))
        
        # Filter worklogs from last 30 days
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=30)
        recent_worklogs = []
        total_hours_30_days = 0
        
        for log in worklogs:
            try:
                log_date = datetime.fromisoformat(log.get('start_date', '').replace('T00:00:00', ''))
                if log_date >= cutoff_date:
                    recent_worklogs.append(log)
                    total_hours_30_days += log.get('time_spent_hours', 0)
            except:
                pass
        
        return {
            "worklogs": {
                "total": len(worklogs),
                "recent_30_days": len(recent_worklogs),
                "total_hours_30_days": round(total_hours_30_days, 1),
                "average_hours_per_entry": round(total_hours / max(1, len(worklogs)), 2)
            },
            "teams": {
                "total": len(teams),
                "active_members": unique_users
            },
            "contributors": {
                "unique_total": unique_users,
                "average_hours_per_contributor": round(total_hours / max(1, unique_users), 1)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch statistics: {str(e)}")

@app.get("/api/tempo/team-member-breakdown")
async def get_team_member_breakdown(days_back: int = 30):
    """Get detailed team member breakdown with tickets and billable hours"""
    try:
        # Use cached Tempo and JIRA data instead of making new API calls
        print("📊 Using cached data for team member breakdown")
        worklogs = []
        jira_tickets = []
        
        if mcp_data_cache.get('tempo_data'):
            worklogs = mcp_data_cache['tempo_data'].get('worklogs', [])
        else:
            print("⏱️ No cached Tempo data, fetching from API...")
            jira_data = mcp_data_cache.get('jira_data') if mcp_data_cache else None
            tempo_data = await fetch_tempo_data(jira_data)
            worklogs = tempo_data.get('worklogs', [])
        
        if mcp_data_cache.get('jira_data'):
            jira_tickets = mcp_data_cache['jira_data'].get('tickets', [])
        else:
            print("⏱️ No cached JIRA data, using empty tickets list...")
            jira_tickets = []
        
        # Filter worklogs by date range
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=days_back)
        filtered_worklogs = []
        
        for log in worklogs:
            try:
                log_date = datetime.fromisoformat(log.get('start_date', '').replace('T00:00:00', ''))
                if log_date >= cutoff_date:
                    filtered_worklogs.append(log)
            except:
                # Include logs without valid dates to avoid missing data
                filtered_worklogs.append(log)
        
        # Group by team member
        team_members = {}
        
        for log in filtered_worklogs:
            author_id = log.get('author_account_id')
            author_name = log.get('author_display_name', 'Unknown')
            ticket_key = log.get('jira_ticket_key', 'Unknown')
            hours = log.get('time_spent_hours', 0)
            
            if author_id and author_name != 'Unknown':
                if author_id not in team_members:
                    team_members[author_id] = {
                        'name': author_name,
                        'total_hours': 0,
                        'billable_hours': 0,
                        'tickets': set(),
                        'ticket_details': []
                    }
                
                team_members[author_id]['total_hours'] += hours
                team_members[author_id]['billable_hours'] += hours  # Assuming all logged hours are billable
                
                if ticket_key and ticket_key != 'Unknown':
                    team_members[author_id]['tickets'].add(ticket_key)
                    # Add ticket details if not already present
                    if not any(t['key'] == ticket_key for t in team_members[author_id]['ticket_details']):
                        # Find ticket summary from JIRA data
                        ticket_summary = 'No summary available'
                        for ticket in jira_tickets:
                            if ticket.get('key') == ticket_key:
                                ticket_summary = ticket.get('summary', 'No summary available')
                                break
                        
                        team_members[author_id]['ticket_details'].append({
                            'key': ticket_key,
                            'summary': ticket_summary,
                            'hours': hours
                        })
                    else:
                        # Update hours for existing ticket
                        for ticket_detail in team_members[author_id]['ticket_details']:
                            if ticket_detail['key'] == ticket_key:
                                ticket_detail['hours'] += hours
                                break
        
        # Convert to list format and limit to top 10 team members by hours
        breakdown_list = []
        for author_id, data in team_members.items():
            breakdown_list.append({
                'name': data['name'],
                'total_hours': round(data['total_hours'], 1),
                'billable_hours': round(data['billable_hours'], 1),
                'tickets_worked': list(data['tickets']),
                'ticket_count': len(data['tickets']),
                'ticket_details': sorted(data['ticket_details'], key=lambda x: x['hours'], reverse=True)
            })
        
        # Sort by total hours and limit to top 10
        breakdown_list.sort(key=lambda x: x['total_hours'], reverse=True)
        top_10_members = breakdown_list[:10]
        
        return {
            "team_members": top_10_members,
            "summary": {
                "total_members": len(breakdown_list),
                "displaying_top": len(top_10_members),
                "period_days": days_back
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate team member breakdown: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.debug,
        log_level="info"
    )