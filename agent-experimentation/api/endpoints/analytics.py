"""
Analytics API endpoints for business intelligence and reporting
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.database import get_db
from services.business_intelligence import BusinessIntelligenceService
from services.analysis import AnalysisOrchestrator
from storage.chromadb_manager import ChromaDBManager
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/executive-risk-assessment", response_model=Dict[str, Any])
async def get_executive_risk_assessment():
    """Get comprehensive executive risk assessment"""
    try:
        bi_service = BusinessIntelligenceService()
        risk_assessment = await bi_service.generate_executive_risk_assessment()
        await bi_service.close()
        
        return risk_assessment
        
    except Exception as e:
        logger.error("Failed to get executive risk assessment", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get executive risk assessment: {str(e)}")


@router.post("/run-analysis", response_model=Dict[str, Any])
async def run_comprehensive_analysis(
    analysis_type: str = Query("daily", description="Type of analysis (daily, weekly)")
):
    """Run comprehensive analysis workflow"""
    try:
        analysis_orchestrator = AnalysisOrchestrator()
        
        if analysis_type == "weekly":
            result = await analysis_orchestrator.generate_weekly_report()
        else:
            result = await analysis_orchestrator.run_daily_analysis()
        
        await analysis_orchestrator.close()
        
        return {
            "analysis_type": analysis_type,
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "results": result
        }
        
    except Exception as e:
        logger.error("Failed to run analysis", analysis_type=analysis_type, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to run analysis: {str(e)}")


@router.get("/semantic-search", response_model=Dict[str, Any])
async def semantic_search(
    query: str = Query(..., min_length=3, description="Search query"),
    collection: str = Query("jira_tickets", description="Collection to search"),
    limit: int = Query(20, ge=1, le=100)
):
    """Perform semantic search across project data"""
    try:
        chroma_manager = ChromaDBManager()
        
        # Initialize ChromaDB if needed
        if not chroma_manager.client:
            await chroma_manager.initialize()
        
        # Validate collection name
        valid_collections = ["jira_tickets", "jira_comments", "confluence_pages", "case_reviews"]
        if collection not in valid_collections:
            raise HTTPException(status_code=400, detail=f"Invalid collection. Must be one of: {valid_collections}")
        
        # Perform search
        results = await chroma_manager.semantic_search(
            query=query,
            collection_name=collection,
            limit=limit
        )
        
        await chroma_manager.close()
        
        return {
            "query": query,
            "collection": collection,
            "results": results,
            "total_results": len(results),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Semantic search failed", query=query, collection=collection, error=str(e))
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")


@router.get("/patterns", response_model=Dict[str, Any])
async def find_problematic_patterns():
    """Find patterns in problematic tickets and issues"""
    try:
        chroma_manager = ChromaDBManager()
        
        # Initialize ChromaDB if needed
        if not chroma_manager.client:
            await chroma_manager.initialize()
        
        patterns = await chroma_manager.find_problematic_patterns()
        
        await chroma_manager.close()
        
        return {
            "patterns": patterns,
            "timestamp": datetime.utcnow().isoformat(),
            "pattern_types": list(patterns.keys())
        }
        
    except Exception as e:
        logger.error("Failed to find patterns", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to find patterns: {str(e)}")


@router.get("/business-metrics", response_model=Dict[str, Any])
async def get_business_metrics(
    days_back: int = Query(30, ge=1, le=90),
    include_trends: bool = Query(True, description="Include trend analysis")
):
    """Get comprehensive business metrics"""
    try:
        bi_service = BusinessIntelligenceService()
        
        # Get all analysis types
        stalled_analysis = await bi_service.analyze_stalled_tickets(days_back)
        overdue_analysis = await bi_service.analyze_overdue_work(days_back)
        deployment_analysis = await bi_service.analyze_failed_deployments(days_back)
        test_analysis = await bi_service.analyze_level_ii_test_failures(days_back)
        
        # Calculate comprehensive metrics
        metrics = {
            "period_days": days_back,
            "timestamp": datetime.utcnow().isoformat(),
            "delivery_metrics": {
                "stalled_tickets": stalled_analysis.get("total_stalled", 0),
                "overdue_tickets": overdue_analysis.get("total_overdue", 0),
                "average_stall_duration": stalled_analysis.get("duration_analysis", {}).get("average_days", 0),
                "overdue_impact": overdue_analysis.get("business_impact", {}),
                "delivery_risk_score": _calculate_delivery_risk_score(stalled_analysis, overdue_analysis)
            },
            "quality_metrics": {
                "deployment_success_rate": deployment_analysis.get("success_rate", 100),
                "failed_deployments": deployment_analysis.get("failed_deployments", 0),
                "test_failures": test_analysis.get("total_failures", 0),
                "quality_risk_score": _calculate_quality_risk_score(deployment_analysis, test_analysis)
            },
            "resource_metrics": {
                "project_distribution": stalled_analysis.get("by_project", {}),
                "assignee_distribution": stalled_analysis.get("by_assignee", {}),
                "bottleneck_analysis": _analyze_resource_bottlenecks(stalled_analysis),
                "utilization_score": _calculate_utilization_score(stalled_analysis)
            },
            "client_metrics": {
                "affected_clients": list(overdue_analysis.get("by_client", {}).keys()),
                "client_risk_assessment": _assess_client_risks(overdue_analysis),
                "communication_required": len(overdue_analysis.get("by_client", {})) > 0
            }
        }
        
        if include_trends:
            # Add trend analysis (simplified for now)
            metrics["trends"] = {
                "delivery_trend": "stable",
                "quality_trend": "improving" if deployment_analysis.get("success_rate", 100) > 90 else "declining",
                "team_health_trend": "good" if stalled_analysis.get("total_stalled", 0) < 10 else "concerning"
            }
        
        await bi_service.close()
        
        return metrics
        
    except Exception as e:
        logger.error("Failed to get business metrics", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get business metrics: {str(e)}")


@router.get("/client-impact", response_model=Dict[str, Any])
async def get_client_impact_analysis(
    days_back: int = Query(30, ge=1, le=90)
):
    """Get detailed client impact analysis"""
    try:
        bi_service = BusinessIntelligenceService()
        
        overdue_analysis = await bi_service.analyze_overdue_work(days_back)
        deployment_analysis = await bi_service.analyze_failed_deployments(days_back)
        
        # Combine client data from both analyses
        client_impact = {}
        
        # Add overdue impact
        for client, count in overdue_analysis.get("by_client", {}).items():
            if client not in client_impact:
                client_impact[client] = {"client_name": client}
            client_impact[client]["overdue_tickets"] = count
            client_impact[client]["overdue_risk"] = "high" if count > 3 else "medium" if count > 1 else "low"
        
        # Add deployment impact
        deployment_by_client = deployment_analysis.get("by_client", {})
        for client, deployment_data in deployment_by_client.items():
            if client not in client_impact:
                client_impact[client] = {"client_name": client, "overdue_tickets": 0, "overdue_risk": "low"}
            
            client_impact[client]["total_deployments"] = deployment_data.get("total", 0)
            client_impact[client]["failed_deployments"] = deployment_data.get("failed", 0)
            client_impact[client]["deployment_success_rate"] = (
                (deployment_data.get("successful", 0) / deployment_data.get("total", 1)) * 100
            )
            client_impact[client]["deployment_risk"] = (
                "high" if deployment_data.get("failed", 0) > 2 else
                "medium" if deployment_data.get("failed", 0) > 0 else "low"
            )
        
        # Calculate overall risk for each client
        for client_data in client_impact.values():
            overdue_risk = client_data.get("overdue_risk", "low")
            deployment_risk = client_data.get("deployment_risk", "low")
            
            # Overall risk is the highest of individual risks
            risk_levels = {"low": 1, "medium": 2, "high": 3}
            overall_risk_score = max(
                risk_levels.get(overdue_risk, 1),
                risk_levels.get(deployment_risk, 1)
            )
            risk_level_names = {1: "low", 2: "medium", 3: "high"}
            client_data["overall_risk"] = risk_level_names[overall_risk_score]
        
        # Sort by overall risk (highest first)
        sorted_clients = sorted(
            client_impact.values(),
            key=lambda x: {"high": 3, "medium": 2, "low": 1}.get(x.get("overall_risk", "low"), 1),
            reverse=True
        )
        
        await bi_service.close()
        
        return {
            "period_days": days_back,
            "total_clients": len(client_impact),
            "high_risk_clients": len([c for c in client_impact.values() if c.get("overall_risk") == "high"]),
            "clients": sorted_clients,
            "summary": {
                "clients_with_overdue_work": len([c for c in client_impact.values() if c.get("overdue_tickets", 0) > 0]),
                "clients_with_deployment_issues": len([c for c in client_impact.values() if c.get("failed_deployments", 0) > 0]),
                "immediate_attention_required": len([c for c in client_impact.values() if c.get("overall_risk") == "high"])
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get client impact analysis", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get client impact analysis: {str(e)}")


@router.get("/team-performance", response_model=Dict[str, Any])
async def get_team_performance_analysis(
    days_back: int = Query(30, ge=1, le=90)
):
    """Get team performance analysis"""
    try:
        bi_service = BusinessIntelligenceService()
        
        stalled_analysis = await bi_service.analyze_stalled_tickets(days_back)
        
        # Analyze team performance
        assignee_data = stalled_analysis.get("by_assignee", {})
        
        team_performance = []
        for assignee, stalled_count in assignee_data.items():
            if assignee and assignee != "Unassigned":
                performance_score = max(10 - (stalled_count * 2), 1)  # Simple scoring
                risk_level = "high" if stalled_count > 5 else "medium" if stalled_count > 2 else "low"
                
                team_performance.append({
                    "team_member": assignee,
                    "stalled_tickets": stalled_count,
                    "performance_score": performance_score,
                    "risk_level": risk_level,
                    "needs_support": stalled_count > 3
                })
        
        # Sort by performance score (worst first)
        team_performance.sort(key=lambda x: x["performance_score"])
        
        await bi_service.close()
        
        return {
            "period_days": days_back,
            "team_members_analyzed": len(team_performance),
            "team_performance": team_performance,
            "summary": {
                "members_needing_support": len([m for m in team_performance if m["needs_support"]]),
                "high_risk_members": len([m for m in team_performance if m["risk_level"] == "high"]),
                "average_performance_score": (
                    sum(m["performance_score"] for m in team_performance) / len(team_performance)
                    if team_performance else 0
                )
            },
            "recommendations": _generate_team_recommendations(team_performance),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get team performance analysis", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get team performance analysis: {str(e)}")


@router.get("/data-quality", response_model=Dict[str, Any])
async def get_data_quality_metrics():
    """Get data quality and system health metrics"""
    try:
        chroma_manager = ChromaDBManager()
        
        # Initialize ChromaDB if needed
        if not chroma_manager.client:
            await chroma_manager.initialize()
        
        # Get collection statistics
        collection_stats = await chroma_manager.get_collection_stats()
        
        await chroma_manager.close()
        
        # Calculate data quality metrics
        quality_metrics = {
            "vector_storage": {
                "collections": collection_stats,
                "total_documents": sum(
                    stats.get("document_count", 0) 
                    for stats in collection_stats.values()
                ),
                "status": "healthy" if collection_stats else "no_data"
            },
            "data_freshness": {
                "last_ingestion": "N/A",  # Would come from scheduler status
                "data_age_hours": 0,  # Would be calculated from last update
                "status": "fresh"
            },
            "system_health": {
                "api_status": "operational",
                "database_status": "connected",
                "ai_service_status": "operational",
                "alert_system_status": "operational"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return quality_metrics
        
    except Exception as e:
        logger.error("Failed to get data quality metrics", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get data quality metrics: {str(e)}")


# Helper functions

def _calculate_delivery_risk_score(stalled_analysis: Dict, overdue_analysis: Dict) -> int:
    """Calculate delivery risk score (1-10, 10 being highest risk)"""
    stalled_count = stalled_analysis.get("total_stalled", 0)
    overdue_count = overdue_analysis.get("total_overdue", 0)
    avg_stall_duration = stalled_analysis.get("duration_analysis", {}).get("average_days", 0)
    
    # Calculate risk score
    risk_score = min(
        (stalled_count * 0.5) + (overdue_count * 0.7) + (avg_stall_duration * 0.2),
        10
    )
    
    return int(risk_score)


def _calculate_quality_risk_score(deployment_analysis: Dict, test_analysis: Dict) -> int:
    """Calculate quality risk score (1-10, 10 being highest risk)"""
    failure_rate = deployment_analysis.get("failure_rate", 0)
    test_failures = test_analysis.get("total_failures", 0)
    
    # Calculate risk score
    risk_score = min(
        (failure_rate * 0.1) + (test_failures * 0.5),
        10
    )
    
    return int(risk_score)


def _analyze_resource_bottlenecks(stalled_analysis: Dict) -> List[Dict[str, Any]]:
    """Analyze resource bottlenecks from stalled ticket data"""
    assignee_data = stalled_analysis.get("by_assignee", {})
    
    bottlenecks = []
    for assignee, count in assignee_data.items():
        if count > 3:  # Threshold for bottleneck
            bottlenecks.append({
                "resource": assignee,
                "stalled_tickets": count,
                "severity": "high" if count > 5 else "medium"
            })
    
    return sorted(bottlenecks, key=lambda x: x["stalled_tickets"], reverse=True)


def _calculate_utilization_score(stalled_analysis: Dict) -> int:
    """Calculate team utilization score (1-10)"""
    total_stalled = stalled_analysis.get("total_stalled", 0)
    
    # Simple utilization scoring
    if total_stalled == 0:
        return 10
    elif total_stalled < 5:
        return 8
    elif total_stalled < 10:
        return 6
    elif total_stalled < 15:
        return 4
    else:
        return 2


def _assess_client_risks(overdue_analysis: Dict) -> Dict[str, str]:
    """Assess risks for each client"""
    client_risks = {}
    
    for client, count in overdue_analysis.get("by_client", {}).items():
        if count > 3:
            client_risks[client] = "high"
        elif count > 1:
            client_risks[client] = "medium"
        else:
            client_risks[client] = "low"
    
    return client_risks


def _generate_team_recommendations(team_performance: List[Dict]) -> List[str]:
    """Generate recommendations based on team performance"""
    recommendations = []
    
    high_risk_members = [m for m in team_performance if m["risk_level"] == "high"]
    if high_risk_members:
        recommendations.append(f"Provide immediate support to {len(high_risk_members)} team members with high risk levels")
    
    members_needing_support = [m for m in team_performance if m["needs_support"]]
    if len(members_needing_support) > len(team_performance) * 0.3:
        recommendations.append("Consider team restructuring or additional resources - 30%+ of team needs support")
    
    if not recommendations:
        recommendations.append("Team performance appears healthy - continue monitoring")
    
    return recommendations