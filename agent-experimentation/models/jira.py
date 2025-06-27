"""
JIRA data models
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from core.database import Base


class JiraProject(Base):
    """JIRA Project model"""
    __tablename__ = "jira_projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_key = Column(String(50), unique=True, nullable=False)
    project_name = Column(String(255), nullable=False)
    project_type = Column(String(50))
    lead = Column(String(255))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tickets = relationship("JiraTicket", back_populates="project")


class JiraTicket(Base):
    """JIRA Ticket model"""
    __tablename__ = "jira_tickets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_key = Column(String(50), unique=True, nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("jira_projects.id"))
    
    # Basic ticket information
    summary = Column(String(500), nullable=False)
    description = Column(Text)
    issue_type = Column(String(100))
    status = Column(String(100))
    priority = Column(String(50))
    
    # People
    assignee = Column(String(255))
    reporter = Column(String(255))
    
    # Dates
    created_date = Column(DateTime)
    updated_date = Column(DateTime)
    due_date = Column(DateTime, nullable=True)
    resolution_date = Column(DateTime, nullable=True)
    
    # Custom fields for our analysis
    story_points = Column(Integer, nullable=True)
    sprint = Column(String(255), nullable=True)
    epic = Column(String(255), nullable=True)
    
    # Analysis fields
    days_in_current_status = Column(Integer, default=0)
    is_overdue = Column(Boolean, default=False)
    is_stalled = Column(Boolean, default=False)  # >5 days in same status
    level_ii_failed = Column(Boolean, default=False)
    
    # Raw JIRA data
    raw_data = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("JiraProject", back_populates="tickets")
    comments = relationship("JiraComment", back_populates="ticket")
    status_history = relationship("JiraStatusHistory", back_populates="ticket")


class JiraComment(Base):
    """JIRA Comment model"""
    __tablename__ = "jira_comments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("jira_tickets.id"))
    comment_id = Column(String(50), unique=True)  # JIRA comment ID
    
    author = Column(String(255))
    body = Column(Text)
    created_date = Column(DateTime)
    updated_date = Column(DateTime)
    
    # Analysis fields
    sentiment_score = Column(String(20))  # positive/negative/neutral
    contains_blocker = Column(Boolean, default=False)
    ai_summary = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ticket = relationship("JiraTicket", back_populates="comments")


class JiraStatusHistory(Base):
    """JIRA Status History model"""
    __tablename__ = "jira_status_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("jira_tickets.id"))
    
    from_status = Column(String(100))
    to_status = Column(String(100))
    changed_by = Column(String(255))
    changed_at = Column(DateTime)
    days_in_previous_status = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    ticket = relationship("JiraTicket", back_populates="status_history")


class JiraWorklog(Base):
    """JIRA Worklog model"""
    __tablename__ = "jira_worklogs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("jira_tickets.id"))
    worklog_id = Column(String(50), unique=True)  # JIRA worklog ID
    
    author = Column(String(255))
    time_spent_seconds = Column(Integer)
    description = Column(Text)
    started_date = Column(DateTime)
    created_date = Column(DateTime)
    updated_date = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)