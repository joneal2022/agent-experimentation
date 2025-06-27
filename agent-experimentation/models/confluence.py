"""
Confluence data models
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid

from core.database import Base


class ConfluenceSpace(Base):
    """Confluence Space model"""
    __tablename__ = "confluence_spaces"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    space_key = Column(String(50), unique=True, nullable=False)
    space_name = Column(String(255), nullable=False)
    space_type = Column(String(50))
    description = Column(Text)
    homepage_id = Column(String(50))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConfluencePage(Base):
    """Confluence Page model"""
    __tablename__ = "confluence_pages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(String(50), unique=True, nullable=False)
    space_key = Column(String(50), nullable=False)
    
    title = Column(String(500), nullable=False)
    content = Column(Text)
    content_type = Column(String(50))  # page, blogpost, comment
    
    # Metadata
    author = Column(String(255))
    created_date = Column(DateTime)
    updated_date = Column(DateTime)
    version = Column(Integer)
    
    # Parent-child relationships
    parent_id = Column(String(50), nullable=True)
    
    # Raw Confluence data
    raw_data = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CaseReview(Base):
    """Case Review (Standup) model"""
    __tablename__ = "case_reviews"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(String(50), nullable=False)  # Reference to Confluence page
    
    review_date = Column(DateTime, nullable=False)
    
    # Extracted data from standup
    critical_cases = Column(JSON)  # List of critical cases with details
    high_urgency_cases = Column(JSON)  # List of high urgency cases
    blocked_cases = Column(JSON)  # List of blocked cases
    waiting_on_client_cases = Column(JSON)  # Cases waiting on client
    internal_testing_cases = Column(JSON)  # Cases in internal testing
    client_review_cases = Column(JSON)  # Cases ready for client review
    prod_ready_cases = Column(JSON)  # Cases ready for production
    
    # Analysis summary
    total_cases = Column(Integer)
    critical_count = Column(Integer)
    blocked_count = Column(Integer)
    overdue_count = Column(Integer)
    stalled_count = Column(Integer)
    
    # AI-generated insights
    executive_summary = Column(Text)
    key_blockers = Column(JSON)  # Extracted blockers and issues
    negative_sentiment_items = Column(JSON)  # Items with negative sentiment
    recommendations = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DeploymentRecord(Base):
    """Deployment Record model"""
    __tablename__ = "deployment_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(String(50), nullable=False)  # Reference to Confluence page
    
    deployment_date = Column(DateTime, nullable=False)
    cases = Column(JSON)  # List of cases deployed
    notes = Column(Text)
    
    # Status tracking
    deployment_status = Column(String(50))  # DONE, FAILED, DEPLOYED TO PROD
    has_failures = Column(Boolean, default=False)
    failure_details = Column(JSON)  # Details of any failures
    
    # Client/Project information
    client_project = Column(String(255))  # Extracted from case keys
    
    # Analysis
    success_rate = Column(String(10))  # Calculated success rate
    ai_summary = Column(Text)  # AI summary of deployment
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConfluenceAnalytics(Base):
    """Confluence Analytics model for tracking insights"""
    __tablename__ = "confluence_analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    analysis_date = Column(DateTime, nullable=False)
    analysis_type = Column(String(100))  # case_review, deployment, general
    
    # Metrics
    total_pages_analyzed = Column(Integer)
    key_insights = Column(JSON)
    trend_analysis = Column(JSON)
    
    # Executive summary
    executive_summary = Column(Text)
    action_items = Column(JSON)
    risk_indicators = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)