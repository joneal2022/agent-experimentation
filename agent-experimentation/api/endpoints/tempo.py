"""
Tempo API endpoints for time tracking and productivity analysis
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from core.database import get_db
from models.tempo import TempoWorklog, TempoTeam, TempoAccount, TempoTimesheet
from connectors.tempo import TempoMCPConnector
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/worklogs", response_model=Dict[str, Any])
async def get_worklogs(
    days_back: int = Query(30, ge=1, le=90),
    author: Optional[str] = Query(None, description="Filter by author"),
    project: Optional[str] = Query(None, description="Filter by project (JIRA key prefix)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get Tempo worklogs with filtering"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        query = db.query(TempoWorklog).filter(
            TempoWorklog.start_date >= cutoff_date
        )
        
        # Apply filters
        if author:
            query = query.filter(TempoWorklog.author_display_name.ilike(f"%{author}%"))
        
        if project:
            query = query.filter(TempoWorklog.jira_ticket_key.startswith(f"{project}-"))
        
        total_count = query.count()
        
        worklogs = query.order_by(desc(TempoWorklog.start_date)).offset(offset).limit(limit).all()
        
        worklog_list = []
        for worklog in worklogs:
            worklog_data = {
                "tempo_worklog_id": worklog.tempo_worklog_id,
                "jira_ticket_key": worklog.jira_ticket_key,
                "author_display_name": worklog.author_display_name,
                "time_spent_hours": worklog.time_spent_hours,
                "time_spent_seconds": worklog.time_spent_seconds,
                "start_date": worklog.start_date.isoformat() if worklog.start_date else None,
                "start_time": worklog.start_time,
                "description": worklog.description,
                "billing_key": worklog.billing_key,
                "project_key": worklog.jira_ticket_key.split('-')[0] if worklog.jira_ticket_key else None
            }
            worklog_list.append(worklog_data)
        
        # Calculate summary statistics
        total_hours = sum(w.time_spent_hours for w in worklogs)
        unique_contributors = len(set(w.author_display_name for w in worklogs if w.author_display_name))
        
        response = {
            "worklogs": worklog_list,
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "summary": {
                "total_hours_logged": total_hours,
                "unique_contributors": unique_contributors,
                "average_hours_per_worklog": total_hours / len(worklogs) if worklogs else 0,
                "date_range": {
                    "start": cutoff_date.isoformat(),
                    "end": datetime.utcnow().isoformat()
                }
            },
            "filters_applied": {
                "days_back": days_back,
                "author": author,
                "project": project
            }
        }
        
        return response
        
    except Exception as e:
        logger.error("Failed to get worklogs", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get worklogs: {str(e)}")


@router.get("/productivity-metrics", response_model=Dict[str, Any])
async def get_productivity_metrics(
    days_back: int = Query(30, ge=1, le=90)
):
    """Get productivity metrics from Tempo data"""
    try:
        tempo_connector = TempoMCPConnector()
        
        if not await tempo_connector.connect():
            raise HTTPException(status_code=503, detail="Unable to connect to Tempo API")
        
        metrics = await tempo_connector.get_productivity_metrics(days_back)
        
        await tempo_connector.close()
        
        return {
            "period_days": days_back,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get productivity metrics", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get productivity metrics: {str(e)}")


@router.get("/teams", response_model=List[Dict[str, Any]])
async def get_teams(
    db: Session = Depends(get_db)
):
    """Get all Tempo teams"""
    try:
        teams = db.query(TempoTeam).all()
        
        team_list = []
        for team in teams:
            team_data = {
                "team_id": team.team_id,
                "team_name": team.team_name,
                "team_lead": team.team_lead,
                "members": team.members or [],
                "member_count": len(team.members) if team.members else 0,
                "permissions": team.permissions or {},
                "created_at": team.created_at.isoformat() if team.created_at else None,
                "updated_at": team.updated_at.isoformat() if team.updated_at else None
            }
            team_list.append(team_data)
        
        return team_list
        
    except Exception as e:
        logger.error("Failed to get teams", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get teams: {str(e)}")


@router.get("/accounts", response_model=List[Dict[str, Any]])
async def get_accounts(
    status: Optional[str] = Query(None, description="Filter by account status"),
    db: Session = Depends(get_db)
):
    """Get Tempo accounts for billing"""
    try:
        query = db.query(TempoAccount)
        
        if status:
            query = query.filter(TempoAccount.status == status)
        
        accounts = query.all()
        
        account_list = []
        for account in accounts:
            account_data = {
                "account_id": account.account_id,
                "account_key": account.account_key,
                "account_name": account.account_name,
                "status": account.status,
                "customer": account.customer,
                "lead": account.lead,
                "default_hourly_rate": account.default_hourly_rate,
                "billing_type": account.billing_type,
                "jira_project_keys": account.jira_project_keys or [],
                "created_at": account.created_at.isoformat() if account.created_at else None,
                "updated_at": account.updated_at.isoformat() if account.updated_at else None
            }
            account_list.append(account_data)
        
        return account_list
        
    except Exception as e:
        logger.error("Failed to get accounts", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get accounts: {str(e)}")


@router.get("/timesheets", response_model=Dict[str, Any])
async def get_timesheets(
    user: Optional[str] = Query(None, description="Filter by user"),
    days_back: int = Query(30, ge=1, le=90),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get Tempo timesheets"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        query = db.query(TempoTimesheet).filter(
            TempoTimesheet.period_start >= cutoff_date
        )
        
        if user:
            query = query.filter(TempoTimesheet.user_display_name.ilike(f"%{user}%"))
        
        total_count = query.count()
        
        timesheets = query.order_by(desc(TempoTimesheet.period_start)).offset(offset).limit(limit).all()
        
        timesheet_list = []
        for timesheet in timesheets:
            timesheet_data = {
                "user_account_id": timesheet.user_account_id,
                "user_display_name": timesheet.user_display_name,
                "period_start": timesheet.period_start.isoformat() if timesheet.period_start else None,
                "period_end": timesheet.period_end.isoformat() if timesheet.period_end else None,
                "total_hours": timesheet.total_hours,
                "billable_hours": timesheet.billable_hours,
                "non_billable_hours": timesheet.non_billable_hours,
                "project_breakdown": timesheet.project_breakdown or {},
                "client_breakdown": timesheet.client_breakdown or {},
                "submitted": timesheet.submitted,
                "approval_status": timesheet.approval_status,
                "utilization_rate": (timesheet.total_hours / 40 * 100) if timesheet.total_hours else 0  # Assuming 40-hour work week
            }
            timesheet_list.append(timesheet_data)
        
        response = {
            "timesheets": timesheet_list,
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "summary": {
                "total_hours": sum(t.total_hours for t in timesheets),
                "total_billable_hours": sum(t.billable_hours for t in timesheets),
                "average_utilization": (
                    sum(t.total_hours for t in timesheets) / (len(timesheets) * 40) * 100
                    if timesheets else 0
                ),
                "unique_users": len(set(t.user_display_name for t in timesheets))
            },
            "filters_applied": {
                "user": user,
                "days_back": days_back
            }
        }
        
        return response
        
    except Exception as e:
        logger.error("Failed to get timesheets", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get timesheets: {str(e)}")


@router.get("/time-analysis", response_model=Dict[str, Any])
async def get_time_analysis(
    days_back: int = Query(30, ge=1, le=90),
    group_by: str = Query("project", description="Group by: project, user, client"),
    db: Session = Depends(get_db)
):
    """Get time analysis grouped by specified dimension"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        worklogs = db.query(TempoWorklog).filter(
            TempoWorklog.start_date >= cutoff_date
        ).all()
        
        if not worklogs:
            return {
                "message": "No time data found for the specified period",
                "analysis": {},
                "period_days": days_back
            }
        
        # Group data based on the specified dimension
        grouped_data = {}
        
        for worklog in worklogs:
            if group_by == "project":
                key = worklog.jira_ticket_key.split('-')[0] if worklog.jira_ticket_key else "Unknown"
            elif group_by == "user":
                key = worklog.author_display_name or "Unknown"
            elif group_by == "client":
                project_key = worklog.jira_ticket_key.split('-')[0] if worklog.jira_ticket_key else "Unknown"
                key = _map_project_to_client(project_key)
            else:
                raise HTTPException(status_code=400, detail="Invalid group_by parameter. Must be: project, user, or client")
            
            if key not in grouped_data:
                grouped_data[key] = {
                    "total_hours": 0,
                    "worklog_count": 0,
                    "contributors": set() if group_by != "user" else None
                }
            
            grouped_data[key]["total_hours"] += worklog.time_spent_hours
            grouped_data[key]["worklog_count"] += 1
            
            if group_by != "user" and worklog.author_display_name:
                grouped_data[key]["contributors"].add(worklog.author_display_name)
        
        # Convert sets to lists and add percentages
        total_hours = sum(data["total_hours"] for data in grouped_data.values())
        
        analysis_data = {}
        for key, data in grouped_data.items():
            analysis_data[key] = {
                "total_hours": data["total_hours"],
                "worklog_count": data["worklog_count"],
                "percentage_of_total": (data["total_hours"] / total_hours * 100) if total_hours > 0 else 0,
                "average_hours_per_worklog": data["total_hours"] / data["worklog_count"] if data["worklog_count"] > 0 else 0
            }
            
            if group_by != "user":
                analysis_data[key]["unique_contributors"] = len(data["contributors"])
                analysis_data[key]["contributors"] = list(data["contributors"])
        
        # Sort by total hours (descending)
        sorted_analysis = dict(sorted(analysis_data.items(), key=lambda x: x[1]["total_hours"], reverse=True))
        
        response = {
            "period_days": days_back,
            "group_by": group_by,
            "total_hours_analyzed": total_hours,
            "total_entries": len(grouped_data),
            "analysis": sorted_analysis,
            "summary": {
                "top_contributor": max(analysis_data.items(), key=lambda x: x[1]["total_hours"])[0] if analysis_data else None,
                "average_hours_per_entry": total_hours / len(grouped_data) if grouped_data else 0,
                "distribution_balance": _calculate_distribution_balance(analysis_data)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get time analysis", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get time analysis: {str(e)}")


@router.get("/utilization-report", response_model=Dict[str, Any])
async def get_utilization_report(
    days_back: int = Query(30, ge=1, le=90),
    target_hours_per_week: float = Query(40.0, ge=1, le=80, description="Target hours per week for utilization calculation"),
    db: Session = Depends(get_db)
):
    """Get team utilization report"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Get timesheet data
        timesheets = db.query(TempoTimesheet).filter(
            TempoTimesheet.period_start >= cutoff_date
        ).all()
        
        if not timesheets:
            return {
                "message": "No timesheet data found for the specified period",
                "utilization_report": {},
                "period_days": days_back
            }
        
        # Calculate utilization by user
        user_utilization = {}
        
        for timesheet in timesheets:
            user = timesheet.user_display_name
            if user not in user_utilization:
                user_utilization[user] = {
                    "total_hours": 0,
                    "billable_hours": 0,
                    "weeks_tracked": 0,
                    "periods": []
                }
            
            user_utilization[user]["total_hours"] += timesheet.total_hours
            user_utilization[user]["billable_hours"] += timesheet.billable_hours
            user_utilization[user]["weeks_tracked"] += 1
            user_utilization[user]["periods"].append({
                "period_start": timesheet.period_start.isoformat() if timesheet.period_start else None,
                "period_end": timesheet.period_end.isoformat() if timesheet.period_end else None,
                "hours": timesheet.total_hours
            })
        
        # Calculate utilization percentages
        utilization_data = {}
        for user, data in user_utilization.items():
            target_total_hours = data["weeks_tracked"] * target_hours_per_week
            utilization_percentage = (data["total_hours"] / target_total_hours * 100) if target_total_hours > 0 else 0
            billable_percentage = (data["billable_hours"] / data["total_hours"] * 100) if data["total_hours"] > 0 else 0
            
            utilization_data[user] = {
                "total_hours": data["total_hours"],
                "billable_hours": data["billable_hours"],
                "weeks_tracked": data["weeks_tracked"],
                "average_hours_per_week": data["total_hours"] / data["weeks_tracked"] if data["weeks_tracked"] > 0 else 0,
                "utilization_percentage": utilization_percentage,
                "billable_percentage": billable_percentage,
                "status": _get_utilization_status(utilization_percentage),
                "periods": data["periods"]
            }
        
        # Sort by utilization percentage
        sorted_utilization = dict(sorted(utilization_data.items(), key=lambda x: x[1]["utilization_percentage"], reverse=True))
        
        # Calculate team averages
        total_team_hours = sum(data["total_hours"] for data in utilization_data.values())
        total_team_billable = sum(data["billable_hours"] for data in utilization_data.values())
        team_size = len(utilization_data)
        
        avg_utilization = sum(data["utilization_percentage"] for data in utilization_data.values()) / team_size if team_size > 0 else 0
        avg_billable_percentage = (total_team_billable / total_team_hours * 100) if total_team_hours > 0 else 0
        
        response = {
            "period_days": days_back,
            "target_hours_per_week": target_hours_per_week,
            "team_size": team_size,
            "utilization_by_user": sorted_utilization,
            "team_summary": {
                "average_utilization": avg_utilization,
                "average_billable_percentage": avg_billable_percentage,
                "total_team_hours": total_team_hours,
                "total_billable_hours": total_team_billable,
                "underutilized_members": len([u for u in utilization_data.values() if u["utilization_percentage"] < 80]),
                "overutilized_members": len([u for u in utilization_data.values() if u["utilization_percentage"] > 110]),
                "optimal_utilization_members": len([u for u in utilization_data.values() if 80 <= u["utilization_percentage"] <= 110])
            },
            "recommendations": _generate_utilization_recommendations(utilization_data, avg_utilization),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return response
        
    except Exception as e:
        logger.error("Failed to get utilization report", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get utilization report: {str(e)}")


@router.get("/statistics", response_model=Dict[str, Any])
async def get_tempo_statistics(
    db: Session = Depends(get_db)
):
    """Get overall Tempo statistics"""
    try:
        # Count worklogs
        total_worklogs = db.query(TempoWorklog).count()
        recent_worklogs = db.query(TempoWorklog).filter(
            TempoWorklog.start_date >= datetime.utcnow() - timedelta(days=30)
        ).count()
        
        # Count teams and accounts
        total_teams = db.query(TempoTeam).count()
        total_accounts = db.query(TempoAccount).count()
        active_accounts = db.query(TempoAccount).filter(TempoAccount.status == "OPEN").count()
        
        # Count timesheets
        total_timesheets = db.query(TempoTimesheet).count()
        recent_timesheets = db.query(TempoTimesheet).filter(
            TempoTimesheet.period_start >= datetime.utcnow() - timedelta(days=30)
        ).count()
        
        # Calculate total hours from recent worklogs
        recent_hours_result = db.query(func.sum(TempoWorklog.time_spent_hours)).filter(
            TempoWorklog.start_date >= datetime.utcnow() - timedelta(days=30)
        ).scalar()
        recent_hours = recent_hours_result or 0
        
        statistics = {
            "worklogs": {
                "total": total_worklogs,
                "recent_30_days": recent_worklogs,
                "total_hours_30_days": float(recent_hours)
            },
            "teams": {
                "total": total_teams
            },
            "accounts": {
                "total": total_accounts,
                "active": active_accounts
            },
            "timesheets": {
                "total": total_timesheets,
                "recent_30_days": recent_timesheets
            },
            "last_updated": datetime.utcnow().isoformat()
        }
        
        return statistics
        
    except Exception as e:
        logger.error("Failed to get Tempo statistics", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get Tempo statistics: {str(e)}")


# Helper functions

def _map_project_to_client(project_key: str) -> str:
    """Map project key to client name"""
    client_map = {
        'PIH': 'PIH', 'CMDR': 'Commander', 'GARNISH': 'Garnish',
        'AGP': 'AGP', 'RSND': 'Resend', 'SEG': 'SEG',
        'TALOS': 'Talos Energy', 'WOOD': 'Wood Group', 'AREN': 'Arena',
        'LPCC': 'LPCC', 'SOTT': 'SOTT', 'FAROUK': 'Farouk'
    }
    return client_map.get(project_key.upper(), 'Unknown Client')


def _calculate_distribution_balance(analysis_data: Dict) -> str:
    """Calculate how balanced the workload distribution is"""
    if not analysis_data:
        return "no_data"
    
    hours_values = [data["total_hours"] for data in analysis_data.values()]
    
    if not hours_values:
        return "no_data"
    
    max_hours = max(hours_values)
    min_hours = min(hours_values)
    
    if max_hours == 0:
        return "no_activity"
    
    balance_ratio = min_hours / max_hours
    
    if balance_ratio > 0.7:
        return "well_balanced"
    elif balance_ratio > 0.4:
        return "moderately_balanced"
    else:
        return "unbalanced"


def _get_utilization_status(utilization_percentage: float) -> str:
    """Get utilization status based on percentage"""
    if utilization_percentage < 70:
        return "underutilized"
    elif utilization_percentage > 120:
        return "overutilized"
    elif 80 <= utilization_percentage <= 110:
        return "optimal"
    else:
        return "acceptable"


def _generate_utilization_recommendations(utilization_data: Dict, avg_utilization: float) -> List[str]:
    """Generate recommendations based on utilization analysis"""
    recommendations = []
    
    underutilized = [user for user, data in utilization_data.items() if data["utilization_percentage"] < 70]
    overutilized = [user for user, data in utilization_data.items() if data["utilization_percentage"] > 120]
    
    if underutilized:
        recommendations.append(f"Consider increasing workload for {len(underutilized)} underutilized team members")
    
    if overutilized:
        recommendations.append(f"Review workload for {len(overutilized)} overutilized team members to prevent burnout")
    
    if avg_utilization < 80:
        recommendations.append("Overall team utilization is low - consider capacity optimization")
    elif avg_utilization > 110:
        recommendations.append("Team appears overutilized - consider adding resources or reducing scope")
    
    if not recommendations:
        recommendations.append("Team utilization appears well-balanced")
    
    return recommendations