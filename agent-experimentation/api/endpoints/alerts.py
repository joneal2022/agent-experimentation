"""
Alerts API endpoints for managing notifications and alert lifecycle
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from core.database import get_db
from models.alerts import Alert, AlertType, AlertSeverity, AlertStatus, NotificationLog
from services.alerts import AlertService
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=Dict[str, Any])
async def get_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity (critical, high, medium, low, info)"),
    status: Optional[str] = Query(None, description="Filter by status (active, acknowledged, resolved)"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    days_back: int = Query(7, ge=1, le=90, description="Number of days to look back"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get alerts with filtering and pagination"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        query = db.query(Alert).filter(Alert.first_detected >= cutoff_date)
        
        # Apply filters
        if severity:
            try:
                query = query.filter(Alert.severity == AlertSeverity(severity))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
        
        if status:
            try:
                query = query.filter(Alert.status == AlertStatus(status))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        if alert_type:
            try:
                query = query.filter(Alert.alert_type == AlertType(alert_type))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid alert type: {alert_type}")
        
        total_count = query.count()
        
        alerts = query.order_by(desc(Alert.first_detected)).offset(offset).limit(limit).all()
        
        alert_list = []
        for alert in alerts:
            alert_data = {
                "id": str(alert.id),
                "alert_type": alert.alert_type.value,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "title": alert.title,
                "description": alert.description,
                "recommendation": alert.recommendation,
                "jira_ticket_key": alert.jira_ticket_key,
                "project_key": alert.project_key,
                "assignee": alert.assignee,
                "client": alert.client,
                "context_data": alert.context_data,
                "first_detected": alert.first_detected.isoformat(),
                "last_updated": alert.last_updated.isoformat(),
                "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                "acknowledged_by": alert.acknowledged_by,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "resolved_by": alert.resolved_by,
                "auto_resolve": alert.auto_resolve
            }
            alert_list.append(alert_data)
        
        # Get summary statistics
        summary_stats = _calculate_alert_summary(alerts)
        
        response = {
            "alerts": alert_list,
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "summary": summary_stats,
            "filters_applied": {
                "severity": severity,
                "status": status,
                "alert_type": alert_type,
                "days_back": days_back
            }
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get alerts", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")


@router.get("/active", response_model=List[Dict[str, Any]])
async def get_active_alerts():
    """Get all active alerts"""
    try:
        alert_service = AlertService()
        active_alerts = await alert_service.get_active_alerts()
        await alert_service.close()
        
        return active_alerts
        
    except Exception as e:
        logger.error("Failed to get active alerts", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get active alerts: {str(e)}")


@router.get("/summary", response_model=Dict[str, Any])
async def get_alerts_summary():
    """Get alerts summary for dashboard"""
    try:
        alert_service = AlertService()
        summary = await alert_service.get_alerts_summary()
        await alert_service.close()
        
        return summary
        
    except Exception as e:
        logger.error("Failed to get alerts summary", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get alerts summary: {str(e)}")


@router.get("/{alert_id}", response_model=Dict[str, Any])
async def get_alert_details(
    alert_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed information for a specific alert"""
    try:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        
        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        
        # Get notification logs for this alert
        notification_logs = db.query(NotificationLog).filter(
            NotificationLog.alert_id == alert_id
        ).order_by(desc(NotificationLog.created_at)).all()
        
        alert_details = {
            "id": str(alert.id),
            "alert_type": alert.alert_type.value,
            "severity": alert.severity.value,
            "status": alert.status.value,
            "title": alert.title,
            "description": alert.description,
            "recommendation": alert.recommendation,
            "jira_ticket_key": alert.jira_ticket_key,
            "project_key": alert.project_key,
            "assignee": alert.assignee,
            "client": alert.client,
            "context_data": alert.context_data,
            "trigger_conditions": alert.trigger_conditions,
            "first_detected": alert.first_detected.isoformat(),
            "last_updated": alert.last_updated.isoformat(),
            "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            "acknowledged_by": alert.acknowledged_by,
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
            "resolved_by": alert.resolved_by,
            "auto_resolve": alert.auto_resolve,
            "resolve_condition": alert.resolve_condition,
            "notifications": [
                {
                    "id": str(log.id),
                    "channel_id": log.channel_id,
                    "recipient": log.recipient,
                    "subject": log.subject,
                    "status": log.status,
                    "sent_at": log.sent_at.isoformat() if log.sent_at else None,
                    "error_message": log.error_message,
                    "created_at": log.created_at.isoformat()
                }
                for log in notification_logs
            ]
        }
        
        return alert_details
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get alert details", alert_id=alert_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get alert details: {str(e)}")


@router.post("/{alert_id}/acknowledge", response_model=Dict[str, Any])
async def acknowledge_alert(
    alert_id: str,
    acknowledged_by: str = Query(..., description="Person acknowledging the alert")
):
    """Acknowledge an alert"""
    try:
        alert_service = AlertService()
        success = await alert_service.acknowledge_alert(alert_id, acknowledged_by)
        await alert_service.close()
        
        if success:
            return {
                "message": "Alert acknowledged successfully",
                "alert_id": alert_id,
                "acknowledged_by": acknowledged_by,
                "acknowledged_at": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to acknowledge alert", alert_id=alert_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge alert: {str(e)}")


@router.post("/create", response_model=Dict[str, Any])
async def create_alert(
    alert_type: str = Query(..., description="Type of alert"),
    severity: str = Query(..., description="Alert severity"),
    title: str = Query(..., description="Alert title"),
    description: str = Query(..., description="Alert description"),
    jira_ticket_key: Optional[str] = Query(None),
    project_key: Optional[str] = Query(None),
    assignee: Optional[str] = Query(None),
    client: Optional[str] = Query(None),
    recommendation: Optional[str] = Query(None)
):
    """Create a new alert (for testing/manual creation)"""
    try:
        alert_service = AlertService()
        
        alert_id = await alert_service.create_alert(
            alert_type=alert_type,
            severity=severity,
            title=title,
            description=description,
            jira_ticket_key=jira_ticket_key,
            project_key=project_key,
            assignee=assignee,
            client=client,
            recommendation=recommendation
        )
        
        await alert_service.close()
        
        if alert_id:
            return {
                "message": "Alert created successfully",
                "alert_id": alert_id,
                "created_at": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create alert")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create alert", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create alert: {str(e)}")


@router.get("/statistics/overview", response_model=Dict[str, Any])
async def get_alert_statistics(
    days_back: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get alert statistics and trends"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Get alerts from the specified period
        alerts = db.query(Alert).filter(Alert.first_detected >= cutoff_date).all()
        
        # Calculate statistics
        total_alerts = len(alerts)
        
        # Group by severity
        severity_stats = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for alert in alerts:
            severity_stats[alert.severity.value] += 1
        
        # Group by status
        status_stats = {"active": 0, "acknowledged": 0, "resolved": 0, "suppressed": 0}
        for alert in alerts:
            status_stats[alert.status.value] += 1
        
        # Group by type
        type_stats = {}
        for alert in alerts:
            alert_type = alert.alert_type.value
            type_stats[alert_type] = type_stats.get(alert_type, 0) + 1
        
        # Calculate resolution metrics
        resolved_alerts = [a for a in alerts if a.status == AlertStatus.RESOLVED]
        avg_resolution_time = None
        if resolved_alerts:
            resolution_times = []
            for alert in resolved_alerts:
                if alert.resolved_at and alert.first_detected:
                    resolution_time = (alert.resolved_at - alert.first_detected).total_seconds() / 3600  # Hours
                    resolution_times.append(resolution_time)
            
            if resolution_times:
                avg_resolution_time = sum(resolution_times) / len(resolution_times)
        
        # Calculate daily alert counts for trending
        daily_counts = {}
        for alert in alerts:
            date_key = alert.first_detected.date().isoformat()
            daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
        
        statistics = {
            "period_days": days_back,
            "total_alerts": total_alerts,
            "by_severity": severity_stats,
            "by_status": status_stats,
            "by_type": type_stats,
            "resolution_metrics": {
                "total_resolved": len(resolved_alerts),
                "resolution_rate": (len(resolved_alerts) / total_alerts * 100) if total_alerts > 0 else 0,
                "avg_resolution_time_hours": avg_resolution_time
            },
            "daily_trend": daily_counts,
            "current_active": len([a for a in alerts if a.status == AlertStatus.ACTIVE]),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return statistics
        
    except Exception as e:
        logger.error("Failed to get alert statistics", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get alert statistics: {str(e)}")


@router.post("/test-notification", response_model=Dict[str, Any])
async def test_notification_system(
    channel: str = Query("email", description="Notification channel to test (email, slack)"),
    recipient: str = Query(..., description="Test recipient")
):
    """Test the notification system"""
    try:
        alert_service = AlertService()
        
        # Create a test alert
        test_alert_id = await alert_service.create_alert(
            alert_type="process_bottleneck",
            severity="info",
            title="Test Notification",
            description="This is a test notification to verify the alert system is working correctly.",
            recommendation="No action required - this is a test."
        )
        
        await alert_service.close()
        
        return {
            "message": "Test notification sent successfully",
            "test_alert_id": test_alert_id,
            "channel": channel,
            "recipient": recipient,
            "sent_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to test notification system", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to test notification system: {str(e)}")


# Helper functions

def _calculate_alert_summary(alerts: List[Alert]) -> Dict[str, Any]:
    """Calculate summary statistics for a list of alerts"""
    if not alerts:
        return {
            "total_alerts": 0,
            "critical_alerts": 0,
            "high_priority_alerts": 0,
            "unresolved_alerts": 0,
            "recent_alerts": 0
        }
    
    critical_count = len([a for a in alerts if a.severity == AlertSeverity.CRITICAL])
    high_priority_count = len([a for a in alerts if a.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]])
    unresolved_count = len([a for a in alerts if a.status == AlertStatus.ACTIVE])
    
    # Recent alerts (last 24 hours)
    recent_cutoff = datetime.utcnow() - timedelta(hours=24)
    recent_count = len([a for a in alerts if a.first_detected >= recent_cutoff])
    
    return {
        "total_alerts": len(alerts),
        "critical_alerts": critical_count,
        "high_priority_alerts": high_priority_count,
        "unresolved_alerts": unresolved_count,
        "recent_alerts": recent_count,
        "resolution_rate": ((len(alerts) - unresolved_count) / len(alerts) * 100) if len(alerts) > 0 else 0
    }