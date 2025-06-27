"""
Alert Service with multiple notification channels
"""
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
import httpx
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from core.database import get_db
from models.alerts import Alert, AlertType, AlertSeverity, AlertStatus, NotificationChannel, NotificationLog, ExecutiveSummary
from models.jira import JiraTicket
from config import settings
from utils.logging import get_logger, log_alert_triggered

logger = get_logger(__name__)


class NotificationChannel:
    """Base class for notification channels"""
    
    def __init__(self, channel_config: Dict[str, Any]):
        self.config = channel_config
        self.enabled = channel_config.get("enabled", True)
        
    async def send_notification(self, alert: Dict[str, Any], recipients: List[str]) -> bool:
        """Send notification through this channel"""
        raise NotImplementedError


class EmailNotificationChannel(NotificationChannel):
    """Email notification channel"""
    
    async def send_notification(self, alert: Dict[str, Any], recipients: List[str]) -> bool:
        """Send email notification"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = settings.alerts.email_from
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"[{alert['severity'].upper()}] {alert['title']}"
            
            # Create HTML body
            body = self._create_email_body(alert)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            with smtplib.SMTP(settings.alerts.email_smtp_host, settings.alerts.email_smtp_port) as server:
                server.starttls()
                server.login(settings.alerts.email_username, settings.alerts.email_password)
                server.send_message(msg)
            
            logger.info("Email notification sent", 
                       alert_id=alert.get('id'),
                       recipients=len(recipients))
            return True
            
        except Exception as e:
            logger.error("Failed to send email notification", 
                        alert_id=alert.get('id'), error=str(e))
            return False
    
    def _create_email_body(self, alert: Dict[str, Any]) -> str:
        """Create HTML email body"""
        severity_colors = {
            "critical": "#dc3545",
            "high": "#fd7e14", 
            "medium": "#ffc107",
            "low": "#28a745",
            "info": "#17a2b8"
        }
        
        color = severity_colors.get(alert['severity'], "#6c757d")
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 20px;">
            <div style="border-left: 4px solid {color}; padding-left: 20px; margin-bottom: 20px;">
                <h2 style="color: {color}; margin-top: 0;">
                    {alert['severity'].upper()} Alert: {alert['title']}
                </h2>
                <p style="margin: 10px 0; color: #555;">
                    <strong>Type:</strong> {alert['alert_type']}<br>
                    <strong>Time:</strong> {alert.get('first_detected', datetime.utcnow().isoformat())}<br>
                    <strong>Project:</strong> {alert.get('project_key', 'N/A')}<br>
                    <strong>Assignee:</strong> {alert.get('assignee', 'N/A')}
                </p>
            </div>
            
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                <h3 style="margin-top: 0; color: #333;">Description</h3>
                <p style="margin: 0; color: #555;">{alert['description']}</p>
            </div>
            
            {self._format_context_data(alert.get('context_data', {}))}
            
            {self._format_recommendation(alert.get('recommendation', ''))}
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #888; font-size: 12px;">
                <p>This alert was generated automatically by the Project Management Dashboard.<br>
                Please do not reply to this email.</p>
            </div>
        </body>
        </html>
        """
    
    def _format_context_data(self, context: Dict[str, Any]) -> str:
        """Format context data for email"""
        if not context:
            return ""
        
        items = []
        for key, value in context.items():
            formatted_key = key.replace('_', ' ').title()
            items.append(f"<li><strong>{formatted_key}:</strong> {value}</li>")
        
        return f"""
        <div style="margin-bottom: 20px;">
            <h3 style="color: #333;">Additional Details</h3>
            <ul style="color: #555; padding-left: 20px;">
                {''.join(items)}
            </ul>
        </div>
        """
    
    def _format_recommendation(self, recommendation: str) -> str:
        """Format recommendation for email"""
        if not recommendation:
            return ""
        
        return f"""
        <div style="background-color: #e3f2fd; padding: 15px; border-radius: 5px; border-left: 4px solid #2196f3;">
            <h3 style="margin-top: 0; color: #1976d2;">Recommended Action</h3>
            <p style="margin: 0; color: #333;">{recommendation}</p>
        </div>
        """


class SlackNotificationChannel(NotificationChannel):
    """Slack notification channel"""
    
    def __init__(self, channel_config: Dict[str, Any]):
        super().__init__(channel_config)
        self.webhook_url = settings.alerts.slack_webhook_url
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def send_notification(self, alert: Dict[str, Any], recipients: List[str]) -> bool:
        """Send Slack notification"""
        try:
            if not self.webhook_url:
                logger.warning("Slack webhook URL not configured")
                return False
            
            # Create Slack message
            message = self._create_slack_message(alert)
            
            # Send to Slack
            response = await self.http_client.post(
                self.webhook_url,
                json=message,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            logger.info("Slack notification sent", alert_id=alert.get('id'))
            return True
            
        except Exception as e:
            logger.error("Failed to send Slack notification", 
                        alert_id=alert.get('id'), error=str(e))
            return False
    
    def _create_slack_message(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Create Slack message payload"""
        severity_colors = {
            "critical": "danger",
            "high": "warning",
            "medium": "#ffc107",
            "low": "good",
            "info": "#17a2b8"
        }
        
        color = severity_colors.get(alert['severity'], "#6c757d")
        
        # Create fields for context data
        fields = []
        context = alert.get('context_data', {})
        
        if alert.get('project_key'):
            fields.append({
                "title": "Project",
                "value": alert['project_key'],
                "short": True
            })
        
        if alert.get('assignee'):
            fields.append({
                "title": "Assignee", 
                "value": alert['assignee'],
                "short": True
            })
        
        for key, value in context.items():
            if len(fields) < 5:  # Limit fields for readability
                fields.append({
                    "title": key.replace('_', ' ').title(),
                    "value": str(value),
                    "short": True
                })
        
        attachment = {
            "color": color,
            "title": f"{alert['severity'].upper()}: {alert['title']}",
            "text": alert['description'],
            "fields": fields,
            "footer": "Project Management Dashboard",
            "ts": int(datetime.utcnow().timestamp())
        }
        
        if alert.get('recommendation'):
            attachment["fields"].append({
                "title": "Recommended Action",
                "value": alert['recommendation'],
                "short": False
            })
        
        return {
            "username": "Project Alert Bot",
            "icon_emoji": ":warning:",
            "attachments": [attachment]
        }
    
    async def close(self):
        """Close HTTP client"""
        if self.http_client:
            await self.http_client.aclose()


class AlertService:
    """Main alert service for managing notifications"""
    
    def __init__(self):
        self.notification_channels = {}
        self._initialize_channels()
    
    def _initialize_channels(self):
        """Initialize notification channels"""
        # Email channel
        if settings.alerts.email_username and settings.alerts.email_password:
            self.notification_channels['email'] = EmailNotificationChannel({
                "enabled": True,
                "recipients": ["executives@company.com"]  # Default recipients
            })
        
        # Slack channel
        if settings.alerts.slack_webhook_url:
            self.notification_channels['slack'] = SlackNotificationChannel({
                "enabled": True,
                "channel": "#alerts"
            })
    
    async def create_alert(self, alert_type: str, severity: str, title: str, 
                          description: str, **kwargs) -> Optional[str]:
        """Create a new alert"""
        try:
            db = next(get_db())
            
            # Check for duplicate alerts
            existing_alert = self._check_duplicate_alert(db, alert_type, title, kwargs)
            if existing_alert:
                logger.info("Duplicate alert suppressed", 
                           alert_type=alert_type, title=title)
                db.close()
                return existing_alert.id
            
            # Create new alert
            new_alert = Alert(
                alert_type=AlertType(alert_type),
                severity=AlertSeverity(severity),
                title=title,
                description=description,
                jira_ticket_key=kwargs.get('jira_ticket_key'),
                project_key=kwargs.get('project_key'),
                assignee=kwargs.get('assignee'),
                client=kwargs.get('client'),
                context_data=kwargs.get('context_data', {}),
                trigger_conditions=kwargs.get('trigger_conditions', {}),
                recommendation=kwargs.get('recommendation', ''),
                auto_resolve=kwargs.get('auto_resolve', True),
                resolve_condition=kwargs.get('resolve_condition', {})
            )
            
            db.add(new_alert)
            db.commit()
            db.refresh(new_alert)
            
            alert_id = str(new_alert.id)
            db.close()
            
            # Send notifications
            await self._send_notifications(new_alert)
            
            logger.info("Alert created", 
                       alert_id=alert_id,
                       alert_type=alert_type,
                       severity=severity)
            
            return alert_id
            
        except Exception as e:
            logger.error("Failed to create alert", 
                        alert_type=alert_type, error=str(e))
            return None
    
    def _check_duplicate_alert(self, db: Session, alert_type: str, title: str, 
                              kwargs: Dict[str, Any]) -> Optional[Alert]:
        """Check for duplicate alerts in the last hour"""
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        
        return db.query(Alert).filter(
            and_(
                Alert.alert_type == AlertType(alert_type),
                Alert.title == title,
                Alert.first_detected >= cutoff_time,
                Alert.status == AlertStatus.ACTIVE
            )
        ).first()
    
    async def _send_notifications(self, alert: Alert):
        """Send notifications for an alert"""
        try:
            # Convert alert to dictionary for notification channels
            alert_dict = {
                "id": str(alert.id),
                "alert_type": alert.alert_type.value,
                "severity": alert.severity.value,
                "title": alert.title,
                "description": alert.description,
                "jira_ticket_key": alert.jira_ticket_key,
                "project_key": alert.project_key,
                "assignee": alert.assignee,
                "client": alert.client,
                "context_data": alert.context_data,
                "recommendation": alert.recommendation,
                "first_detected": alert.first_detected.isoformat()
            }
            
            # Determine recipients based on severity and type
            recipients = self._get_recipients(alert)
            
            # Send through each enabled channel
            notification_tasks = []
            for channel_name, channel in self.notification_channels.items():
                if channel.enabled:
                    task = self._send_channel_notification(
                        channel_name, channel, alert_dict, recipients
                    )
                    notification_tasks.append(task)
            
            # Execute notifications in parallel
            if notification_tasks:
                await asyncio.gather(*notification_tasks, return_exceptions=True)
                
        except Exception as e:
            logger.error("Failed to send notifications", 
                        alert_id=str(alert.id), error=str(e))
    
    async def _send_channel_notification(self, channel_name: str, channel: NotificationChannel,
                                       alert_dict: Dict[str, Any], recipients: List[str]):
        """Send notification through a specific channel"""
        try:
            success = await channel.send_notification(alert_dict, recipients)
            
            # Log notification attempt
            await self._log_notification(
                alert_dict['id'], channel_name, recipients, 
                "sent" if success else "failed"
            )
            
        except Exception as e:
            logger.error("Channel notification failed", 
                        channel=channel_name, 
                        alert_id=alert_dict['id'], 
                        error=str(e))
            
            await self._log_notification(
                alert_dict['id'], channel_name, recipients, "failed", str(e)
            )
    
    def _get_recipients(self, alert: Alert) -> List[str]:
        """Get recipients based on alert severity and type"""
        recipients = []
        
        # Critical and high severity alerts go to executives
        if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
            recipients.extend([
                "ceo@company.com",
                "cto@company.com", 
                "operations@company.com"
            ])
        
        # Medium severity alerts go to project managers
        if alert.severity in [AlertSeverity.MEDIUM]:
            recipients.extend([
                "projectmanagers@company.com",
                "teamleads@company.com"
            ])
        
        # Add assignee if available
        if alert.assignee:
            # This would typically map to actual email addresses
            recipients.append(f"{alert.assignee.lower().replace(' ', '.')}@company.com")
        
        return list(set(recipients))  # Remove duplicates
    
    async def _log_notification(self, alert_id: str, channel: str, recipients: List[str],
                               status: str, error_message: str = None):
        """Log notification attempt"""
        try:
            db = next(get_db())
            
            log_entry = NotificationLog(
                alert_id=alert_id,
                channel_id=channel,  # This would be a proper channel ID in production
                recipient=', '.join(recipients),
                status=status,
                error_message=error_message,
                sent_at=datetime.utcnow() if status == "sent" else None
            )
            
            db.add(log_entry)
            db.commit()
            db.close()
            
        except Exception as e:
            logger.error("Failed to log notification", error=str(e))
    
    async def create_critical_alert(self, title: str, description: str, 
                                   alert_type: str = "process_bottleneck", **kwargs) -> Optional[str]:
        """Create a critical alert"""
        return await self.create_alert(
            alert_type=alert_type,
            severity="critical",
            title=title,
            description=description,
            **kwargs
        )
    
    async def check_urgent_conditions(self):
        """Check for urgent conditions that require immediate alerts"""
        try:
            logger.info("Checking urgent conditions")
            
            db = next(get_db())
            
            # Check for tickets stalled longer than threshold
            stalled_threshold = settings.alerts.stalled_ticket_days
            stalled_tickets = db.query(JiraTicket).filter(
                JiraTicket.days_in_current_status > stalled_threshold,
                JiraTicket.is_stalled == True
            ).all()
            
            # Alert if too many stalled tickets
            if len(stalled_tickets) > 10:  # Configurable threshold
                await self.create_alert(
                    alert_type="stalled_ticket",
                    severity="high",
                    title=f"High Number of Stalled Tickets ({len(stalled_tickets)})",
                    description=f"Found {len(stalled_tickets)} tickets stalled for more than {stalled_threshold} days",
                    context_data={"stalled_count": len(stalled_tickets)},
                    recommendation="Review resource allocation and identify blockers"
                )
            
            # Check for overdue tickets
            overdue_tickets = db.query(JiraTicket).filter(
                JiraTicket.is_overdue == True
            ).all()
            
            if len(overdue_tickets) > 5:  # Configurable threshold
                await self.create_alert(
                    alert_type="overdue_ticket", 
                    severity="high",
                    title=f"Multiple Overdue Tickets ({len(overdue_tickets)})",
                    description=f"Found {len(overdue_tickets)} overdue tickets requiring immediate attention",
                    context_data={"overdue_count": len(overdue_tickets)},
                    recommendation="Prioritize overdue work and communicate with clients"
                )
            
            # Check for Level II test failures
            failed_tests = db.query(JiraTicket).filter(
                JiraTicket.level_ii_failed == True
            ).all()
            
            if len(failed_tests) > 3:  # Configurable threshold
                await self.create_alert(
                    alert_type="level_ii_failed",
                    severity="critical",
                    title=f"Multiple Level II Test Failures ({len(failed_tests)})",
                    description=f"Found {len(failed_tests)} tickets with Level II test failures",
                    context_data={"failed_tests": len(failed_tests)},
                    recommendation="Review testing processes and quality assurance procedures"
                )
            
            db.close()
            
            logger.info("Urgent conditions check completed")
            
        except Exception as e:
            logger.error("Failed to check urgent conditions", error=str(e))
    
    async def process_daily_alerts(self):
        """Process alerts from daily analysis"""
        try:
            logger.info("Processing daily alerts")
            
            # This would integrate with the analysis orchestrator results
            # For now, we'll check database conditions
            await self.check_urgent_conditions()
            
            # Auto-resolve alerts that meet resolution conditions
            await self._auto_resolve_alerts()
            
            logger.info("Daily alert processing completed")
            
        except Exception as e:
            logger.error("Failed to process daily alerts", error=str(e))
    
    async def _auto_resolve_alerts(self):
        """Auto-resolve alerts that meet resolution conditions"""
        try:
            db = next(get_db())
            
            # Find active alerts that can be auto-resolved
            active_alerts = db.query(Alert).filter(
                Alert.status == AlertStatus.ACTIVE,
                Alert.auto_resolve == True
            ).all()
            
            for alert in active_alerts:
                if await self._check_resolution_condition(alert):
                    alert.status = AlertStatus.RESOLVED
                    alert.resolved_at = datetime.utcnow()
                    alert.resolved_by = "system"
                    
                    logger.info("Alert auto-resolved", alert_id=str(alert.id))
            
            db.commit()
            db.close()
            
        except Exception as e:
            logger.error("Failed to auto-resolve alerts", error=str(e))
    
    async def _check_resolution_condition(self, alert: Alert) -> bool:
        """Check if alert meets resolution conditions"""
        try:
            # Simple resolution logic - can be enhanced
            if alert.alert_type == AlertType.STALLED_TICKET:
                # Check if stalled tickets have been resolved
                db = next(get_db())
                stalled_count = db.query(JiraTicket).filter(
                    JiraTicket.is_stalled == True
                ).count()
                db.close()
                
                # Resolve if stalled count is below threshold
                return stalled_count < 5
            
            # Add more resolution conditions for other alert types
            return False
            
        except Exception as e:
            logger.error("Failed to check resolution condition", 
                        alert_id=str(alert.id), error=str(e))
            return False
    
    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        try:
            db = next(get_db())
            
            active_alerts = db.query(Alert).filter(
                Alert.status == AlertStatus.ACTIVE
            ).order_by(Alert.severity.desc(), Alert.first_detected.desc()).all()
            
            alerts_data = []
            for alert in active_alerts:
                alerts_data.append({
                    "id": str(alert.id),
                    "alert_type": alert.alert_type.value,
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "description": alert.description,
                    "first_detected": alert.first_detected.isoformat(),
                    "project_key": alert.project_key,
                    "assignee": alert.assignee,
                    "context_data": alert.context_data
                })
            
            db.close()
            return alerts_data
            
        except Exception as e:
            logger.error("Failed to get active alerts", error=str(e))
            return []
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        try:
            db = next(get_db())
            
            alert = db.query(Alert).filter(Alert.id == alert_id).first()
            if alert:
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = datetime.utcnow()
                alert.acknowledged_by = acknowledged_by
                
                db.commit()
                db.close()
                
                logger.info("Alert acknowledged", 
                           alert_id=alert_id, 
                           acknowledged_by=acknowledged_by)
                return True
            
            db.close()
            return False
            
        except Exception as e:
            logger.error("Failed to acknowledge alert", 
                        alert_id=alert_id, error=str(e))
            return False
    
    async def close(self):
        """Close alert service and notification channels"""
        for channel in self.notification_channels.values():
            if hasattr(channel, 'close'):
                await channel.close()
        
        logger.info("Alert service closed")