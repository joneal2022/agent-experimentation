"""
Alert and notification models
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from core.database import Base


class AlertSeverity(enum.Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertType(enum.Enum):
    """Alert types"""
    STALLED_TICKET = "stalled_ticket"
    OVERDUE_TICKET = "overdue_ticket"
    LEVEL_II_FAILED = "level_ii_failed"
    DEPLOYMENT_FAILURE = "deployment_failure"
    TEAM_OVERLOAD = "team_overload"
    CLIENT_WAITING = "client_waiting"
    RESOURCE_CONSTRAINT = "resource_constraint"
    QUALITY_ISSUE = "quality_issue"
    PROCESS_BOTTLENECK = "process_bottleneck"


class AlertStatus(enum.Enum):
    """Alert status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class Alert(Base):
    """Alert model"""
    __tablename__ = "alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Alert classification
    alert_type = Column(Enum(AlertType), nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False)
    status = Column(Enum(AlertStatus), default=AlertStatus.ACTIVE)
    
    # Alert content
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    recommendation = Column(Text)
    
    # Context
    jira_ticket_key = Column(String(50), nullable=True)
    project_key = Column(String(50), nullable=True)
    assignee = Column(String(255), nullable=True)
    client = Column(String(255), nullable=True)
    
    # Metadata
    context_data = Column(JSON)  # Additional context information
    trigger_conditions = Column(JSON)  # What triggered this alert
    
    # Tracking
    first_detected = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(255), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(255), nullable=True)
    
    # Notification tracking
    notifications_sent = Column(JSON)  # Track which notifications were sent
    
    # Auto-resolution
    auto_resolve = Column(Boolean, default=True)
    resolve_condition = Column(JSON)  # Conditions for auto-resolution
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationChannel(Base):
    """Notification Channel configuration"""
    __tablename__ = "notification_channels"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    channel_name = Column(String(100), nullable=False)
    channel_type = Column(String(50), nullable=False)  # email, slack, webhook, sms
    
    # Configuration
    configuration = Column(JSON, nullable=False)  # Channel-specific config
    
    # Filtering rules
    severity_filter = Column(JSON)  # Which severities to send
    alert_type_filter = Column(JSON)  # Which alert types to send
    project_filter = Column(JSON)  # Which projects to monitor
    
    # Status
    enabled = Column(Boolean, default=True)
    last_used = Column(DateTime, nullable=True)
    failure_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationLog(Base):
    """Notification Log model"""
    __tablename__ = "notification_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    alert_id = Column(UUID(as_uuid=True), nullable=False)
    channel_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Notification details
    recipient = Column(String(500))  # Email, slack channel, etc.
    subject = Column(String(500))
    message = Column(Text)
    
    # Status
    sent_at = Column(DateTime, nullable=True)
    status = Column(String(50))  # pending, sent, failed, delivered
    error_message = Column(Text, nullable=True)
    
    # Response tracking
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)
    response_data = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ExecutiveSummary(Base):
    """Executive Summary model for daily/weekly reports"""
    __tablename__ = "executive_summaries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Report metadata
    report_date = Column(DateTime, nullable=False)
    report_type = Column(String(50), nullable=False)  # daily, weekly, monthly
    report_period_start = Column(DateTime, nullable=False)
    report_period_end = Column(DateTime, nullable=False)
    
    # Key metrics
    total_tickets = Column(Integer)
    stalled_tickets = Column(Integer)
    overdue_tickets = Column(Integer)
    failed_deployments = Column(Integer)
    critical_alerts = Column(Integer)
    
    # Summary sections
    executive_overview = Column(Text)
    key_achievements = Column(JSON)
    critical_issues = Column(JSON)
    blockers_and_risks = Column(JSON)
    resource_utilization = Column(JSON)
    client_health = Column(JSON)
    upcoming_deadlines = Column(JSON)
    
    # AI-generated insights
    trend_analysis = Column(Text)
    predictive_insights = Column(JSON)
    recommendations = Column(JSON)
    
    # Distribution tracking
    sent_to = Column(JSON)  # List of recipients
    sent_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)