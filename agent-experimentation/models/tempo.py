"""
Tempo time tracking data models
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid

from core.database import Base


class TempoWorklog(Base):
    """Tempo Worklog model"""
    __tablename__ = "tempo_worklogs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tempo_worklog_id = Column(Integer, unique=True, nullable=False)  # Tempo's internal ID
    
    # JIRA integration
    jira_ticket_key = Column(String(50), nullable=False)
    jira_ticket_id = Column(String(50))
    
    # Time tracking
    time_spent_seconds = Column(Integer, nullable=False)
    time_spent_hours = Column(Float, nullable=False)  # Calculated field
    billing_key = Column(String(100))  # For client billing
    
    # User information
    author_account_id = Column(String(255))
    author_display_name = Column(String(255))
    
    # Date information
    start_date = Column(DateTime, nullable=False)
    start_time = Column(String(10))  # HH:MM format if available
    
    # Description and attributes
    description = Column(Text)
    attributes = Column(JSON)  # Custom Tempo attributes
    
    # Raw Tempo data
    raw_data = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TempoTeam(Base):
    """Tempo Team model"""
    __tablename__ = "tempo_teams"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(Integer, unique=True, nullable=False)
    team_name = Column(String(255), nullable=False)
    team_lead = Column(String(255))
    
    # Team members (JSON array of user objects)
    members = Column(JSON)
    
    # Team settings
    permissions = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TempoAccount(Base):
    """Tempo Account model for client billing"""
    __tablename__ = "tempo_accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(Integer, unique=True, nullable=False)
    account_key = Column(String(50), unique=True, nullable=False)
    account_name = Column(String(255), nullable=False)
    
    # Account details
    status = Column(String(50))  # OPEN, CLOSED, etc.
    customer = Column(String(255))
    lead = Column(String(255))
    
    # Billing information
    default_hourly_rate = Column(Float)
    billing_type = Column(String(50))  # BILLABLE, NON_BILLABLE
    
    # Links
    jira_project_keys = Column(JSON)  # Projects associated with this account
    
    # Raw Tempo data
    raw_data = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TempoTimesheet(Base):
    """Tempo Timesheet model for aggregated time data"""
    __tablename__ = "tempo_timesheets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Period information
    user_account_id = Column(String(255), nullable=False)
    user_display_name = Column(String(255), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Time summary
    total_hours = Column(Float, nullable=False)
    billable_hours = Column(Float, default=0)
    non_billable_hours = Column(Float, default=0)
    
    # Project breakdown (JSON with project keys and hours)
    project_breakdown = Column(JSON)
    client_breakdown = Column(JSON)
    
    # Status
    submitted = Column(String(50))  # SUBMITTED, DRAFT, APPROVED, etc.
    approval_status = Column(String(50))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TempoAnalytics(Base):
    """Tempo Analytics model for tracking productivity insights"""
    __tablename__ = "tempo_analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    analysis_date = Column(DateTime, nullable=False)
    analysis_period_start = Column(DateTime, nullable=False)
    analysis_period_end = Column(DateTime, nullable=False)
    
    # Team metrics
    team_utilization = Column(JSON)  # Utilization by team
    project_velocity = Column(JSON)  # Hours per project
    client_billing_summary = Column(JSON)  # Billing summary by client
    
    # Individual metrics
    top_performers = Column(JSON)  # Most productive team members
    underutilized_resources = Column(JSON)  # Team members with low hours
    
    # Project insights
    project_health = Column(JSON)  # Projects with time tracking issues
    overdue_timesheets = Column(JSON)  # Late timesheet submissions
    
    # AI-generated insights
    executive_summary = Column(Text)
    productivity_trends = Column(JSON)
    recommendations = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)