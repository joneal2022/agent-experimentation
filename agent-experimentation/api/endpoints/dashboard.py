"""
Dashboard API endpoints for executive overview and KPIs
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.database import get_db
from services.business_intelligence import BusinessIntelligenceService
from services.analysis import AnalysisOrchestrator
from services.alerts import AlertService
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/executive-summary", response_model=Dict[str, Any])
async def get_executive_summary(
    days_back: int = Query(7, ge=1, le=90, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """Get executive summary with key metrics and insights"""
    try:
        bi_service = BusinessIntelligenceService()
        risk_assessment = await bi_service.generate_executive_risk_assessment()
        
        # Get key metrics
        analysis_orchestrator = AnalysisOrchestrator()
        recent_analysis = await analysis_orchestrator.run_daily_analysis()
        
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "period_days": days_back,
            "overall_health_score": risk_assessment.get("overall_risk_score", 5),
            "key_metrics": recent_analysis.get("insights", {}).get("key_metrics", {}),
            "risk_assessment": risk_assessment,
            "executive_insights": recent_analysis.get("executive_summary", {}),
            "trend_indicators": {
                "delivery_trend": "stable",
                "quality_trend": "improving",
                "team_health": "good"
            }
        }
        
        await bi_service.close()
        
        return summary
        
    except Exception as e:
        logger.error("Failed to get executive summary", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to generate executive summary: {str(e)}")


@router.get("/kpis", response_model=Dict[str, Any])
async def get_key_performance_indicators(
    days_back: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get key performance indicators for the dashboard"""
    try:
        bi_service = BusinessIntelligenceService()
        
        # Get analysis for different time periods
        stalled_analysis = await bi_service.analyze_stalled_tickets(days_back)
        overdue_analysis = await bi_service.analyze_overdue_work(days_back)
        deployment_analysis = await bi_service.analyze_failed_deployments(days_back)
        test_analysis = await bi_service.analyze_level_ii_test_failures(days_back)
        
        kpis = {
            "timestamp": datetime.utcnow().isoformat(),
            "period_days": days_back,
            "delivery_metrics": {
                "stalled_tickets": stalled_analysis.get("total_stalled", 0),
                "overdue_tickets": overdue_analysis.get("total_overdue", 0),
                "average_stall_duration": stalled_analysis.get("duration_analysis", {}).get("average_days", 0),
                "delivery_risk_level": _calculate_delivery_risk_level(stalled_analysis, overdue_analysis)
            },
            "quality_metrics": {
                "deployment_success_rate": deployment_analysis.get("success_rate", 100),
                "failed_deployments": deployment_analysis.get("failed_deployments", 0),
                "test_failures": test_analysis.get("total_failures", 0),
                "quality_risk_level": _calculate_quality_risk_level(deployment_analysis, test_analysis)
            },
            "team_metrics": {
                "total_active_projects": len(stalled_analysis.get("by_project", {})),
                "team_utilization": 85,  # This would come from Tempo analysis
                "bottleneck_count": len(stalled_analysis.get("by_assignee", {})),
                "team_health_score": _calculate_team_health_score(stalled_analysis)
            },
            "client_metrics": {
                "affected_clients": len(overdue_analysis.get("by_client", {})),
                "client_satisfaction_risk": overdue_analysis.get("business_impact", {}).get("impact_level", "low"),
                "communication_needed": len(overdue_analysis.get("by_client", {})) > 0
            }
        }
        
        await bi_service.close()
        return kpis
        
    except Exception as e:
        logger.error("Failed to get KPIs", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get KPIs: {str(e)}")


@router.get("/project-health", response_model=List[Dict[str, Any]])
async def get_project_health_overview(
    db: Session = Depends(get_db)
):
    """Get health overview for all active projects"""
    try:
        bi_service = BusinessIntelligenceService()
        
        # Get project-level analysis
        stalled_analysis = await bi_service.analyze_stalled_tickets(30)
        overdue_analysis = await bi_service.analyze_overdue_work(30)
        
        # Combine project data
        projects = {}
        
        # Add stalled ticket data
        for project, count in stalled_analysis.get("by_project", {}).items():
            if project not in projects:
                projects[project] = {"project_key": project, "client": _map_project_to_client(project)}
            projects[project]["stalled_tickets"] = count
        
        # Add overdue ticket data
        for project, count in overdue_analysis.get("by_project", {}).items():
            if project not in projects:
                projects[project] = {"project_key": project, "client": _map_project_to_client(project)}
            projects[project]["overdue_tickets"] = count
        
        # Calculate health scores
        project_health = []
        for project_data in projects.values():
            stalled = project_data.get("stalled_tickets", 0)
            overdue = project_data.get("overdue_tickets", 0)
            
            health_score = max(10 - (stalled * 2) - (overdue * 3), 1)
            risk_level = "high" if health_score <= 4 else "medium" if health_score <= 7 else "low"
            
            project_health.append({
                **project_data,
                "health_score": health_score,
                "risk_level": risk_level,
                "total_issues": stalled + overdue,
                "last_updated": datetime.utcnow().isoformat()
            })
        
        # Sort by health score (worst first)
        project_health.sort(key=lambda x: x["health_score"])
        
        await bi_service.close()
        return project_health
        
    except Exception as e:
        logger.error("Failed to get project health", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get project health: {str(e)}")


@router.get("/alerts-summary", response_model=Dict[str, Any])
async def get_alerts_summary(
    db: Session = Depends(get_db)
):
    """Get summary of current alerts and their status"""
    try:
        alert_service = AlertService()
        active_alerts = await alert_service.get_active_alerts()
        
        # Group alerts by severity
        alerts_by_severity = {"critical": [], "high": [], "medium": [], "low": [], "info": []}
        for alert in active_alerts:
            severity = alert.get("severity", "low")
            alerts_by_severity[severity].append(alert)
        
        summary = {
            "total_active_alerts": len(active_alerts),
            "by_severity": {
                severity: len(alerts) for severity, alerts in alerts_by_severity.items()
            },
            "critical_alerts": alerts_by_severity["critical"][:5],  # Show top 5 critical
            "recent_alerts": sorted(active_alerts, key=lambda x: x.get("first_detected", ""), reverse=True)[:10],
            "alerts_requiring_action": [
                alert for alert in active_alerts 
                if alert.get("severity") in ["critical", "high"]
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await alert_service.close()
        return summary
        
    except Exception as e:
        logger.error("Failed to get alerts summary", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get alerts summary: {str(e)}")


@router.get("/trends", response_model=Dict[str, Any])
async def get_trend_analysis(
    days_back: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db)
):
    """Get trend analysis for key metrics over time"""
    try:
        # This would typically analyze historical data
        # For now, providing a structured response for frontend development
        
        trends = {
            "period_days": days_back,
            "timestamp": datetime.utcnow().isoformat(),
            "delivery_trends": {
                "stalled_tickets_trend": {
                    "direction": "decreasing",
                    "change_percentage": -15.2,
                    "data_points": _generate_mock_trend_data(days_back, "stalled")
                },
                "overdue_tickets_trend": {
                    "direction": "stable", 
                    "change_percentage": 2.1,
                    "data_points": _generate_mock_trend_data(days_back, "overdue")
                }
            },
            "quality_trends": {
                "deployment_success_rate": {
                    "direction": "improving",
                    "change_percentage": 8.5,
                    "current_rate": 92.3,
                    "data_points": _generate_mock_trend_data(days_back, "deployments")
                },
                "test_failure_rate": {
                    "direction": "decreasing",
                    "change_percentage": -12.3,
                    "data_points": _generate_mock_trend_data(days_back, "test_failures")
                }
            },
            "team_trends": {
                "productivity": {
                    "direction": "improving",
                    "change_percentage": 6.7,
                    "data_points": _generate_mock_trend_data(days_back, "productivity")
                },
                "utilization": {
                    "direction": "stable",
                    "change_percentage": 1.2,
                    "current_rate": 87.5
                }
            }
        }
        
        return trends
        
    except Exception as e:
        logger.error("Failed to get trend analysis", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get trend analysis: {str(e)}")


# Helper functions

def _calculate_delivery_risk_level(stalled_analysis: Dict, overdue_analysis: Dict) -> str:
    """Calculate overall delivery risk level"""
    stalled_count = stalled_analysis.get("total_stalled", 0)
    overdue_count = overdue_analysis.get("total_overdue", 0)
    
    total_issues = stalled_count + overdue_count
    
    if total_issues > 15:
        return "high"
    elif total_issues > 8:
        return "medium"
    else:
        return "low"


def _calculate_quality_risk_level(deployment_analysis: Dict, test_analysis: Dict) -> str:
    """Calculate overall quality risk level"""
    failure_rate = deployment_analysis.get("failure_rate", 0)
    test_failures = test_analysis.get("total_failures", 0)
    
    if failure_rate > 25 or test_failures > 5:
        return "high"
    elif failure_rate > 15 or test_failures > 2:
        return "medium"
    else:
        return "low"


def _calculate_team_health_score(stalled_analysis: Dict) -> int:
    """Calculate team health score (1-10)"""
    stalled_count = stalled_analysis.get("total_stalled", 0)
    avg_duration = stalled_analysis.get("duration_analysis", {}).get("average_days", 0)
    
    # Base score of 10, subtract points for issues
    score = 10 - min(stalled_count // 2, 4) - min(avg_duration // 3, 3)
    return max(score, 1)


def _map_project_to_client(project_key: str) -> str:
    """Map project key to client name"""
    client_map = {
        'PIH': 'PIH', 'CMDR': 'Commander', 'GARNISH': 'Garnish',
        'AGP': 'AGP', 'RSND': 'Resend', 'SEG': 'SEG',
        'TALOS': 'Talos Energy', 'WOOD': 'Wood Group', 'AREN': 'Arena',
        'LPCC': 'LPCC', 'SOTT': 'SOTT', 'FAROUK': 'Farouk'
    }
    return client_map.get(project_key.upper(), 'Unknown Client')


def _generate_mock_trend_data(days_back: int, metric_type: str) -> List[Dict[str, Any]]:
    """Generate mock trend data for frontend development"""
    # This would be replaced with actual historical data analysis
    import random
    
    data_points = []
    base_value = {"stalled": 12, "overdue": 8, "deployments": 95, "test_failures": 3, "productivity": 85}.get(metric_type, 50)
    
    for i in range(min(days_back, 30)):  # Limit to 30 data points for performance
        date = (datetime.utcnow() - timedelta(days=i)).date().isoformat()
        # Add some realistic variation
        value = base_value + random.randint(-3, 3)
        if metric_type == "deployments":
            value = max(min(value, 100), 75)  # Keep deployment rate realistic
        
        data_points.append({
            "date": date,
            "value": value
        })
    
    return list(reversed(data_points))  # Chronological order