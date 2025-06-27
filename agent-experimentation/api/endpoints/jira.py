"""
JIRA API endpoints for ticket management and analysis
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from core.database import get_db
from models.jira import JiraTicket, JiraComment, JiraProject
from services.business_intelligence import BusinessIntelligenceService
from storage.chromadb_manager import ChromaDBManager
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/tickets", response_model=Dict[str, Any])
async def get_tickets(
    project: Optional[str] = Query(None, description="Filter by project key"),
    status: Optional[str] = Query(None, description="Filter by status"),
    assignee: Optional[str] = Query(None, description="Filter by assignee"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    stalled_only: bool = Query(False, description="Show only stalled tickets"),
    overdue_only: bool = Query(False, description="Show only overdue tickets"),
    failed_testing_only: bool = Query(False, description="Show only Level II test failures"),
    limit: int = Query(50, ge=1, le=200, description="Number of tickets to return"),
    offset: int = Query(0, ge=0, description="Number of tickets to skip"),
    db: Session = Depends(get_db)
):
    """Get JIRA tickets with filtering options"""
    try:
        query = db.query(JiraTicket)
        
        # Apply filters
        if project:
            query = query.filter(JiraTicket.ticket_key.startswith(f"{project}-"))
        
        if status:
            query = query.filter(JiraTicket.status == status)
        
        if assignee:
            query = query.filter(JiraTicket.assignee == assignee)
        
        if priority:
            query = query.filter(JiraTicket.priority == priority)
        
        if stalled_only:
            query = query.filter(JiraTicket.is_stalled == True)
        
        if overdue_only:
            query = query.filter(JiraTicket.is_overdue == True)
        
        if failed_testing_only:
            query = query.filter(JiraTicket.level_ii_failed == True)
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination and ordering
        tickets = query.order_by(desc(JiraTicket.updated_at)).offset(offset).limit(limit).all()
        
        # Convert to response format
        ticket_list = []
        for ticket in tickets:
            ticket_data = {
                "ticket_key": ticket.ticket_key,
                "summary": ticket.summary,
                "description": ticket.description,
                "status": ticket.status,
                "priority": ticket.priority,
                "assignee": ticket.assignee,
                "reporter": ticket.reporter,
                "issue_type": ticket.issue_type,
                "created_date": ticket.created_date.isoformat() if ticket.created_date else None,
                "updated_date": ticket.updated_date.isoformat() if ticket.updated_date else None,
                "due_date": ticket.due_date.isoformat() if ticket.due_date else None,
                "days_in_current_status": ticket.days_in_current_status,
                "is_stalled": ticket.is_stalled,
                "is_overdue": ticket.is_overdue,
                "level_ii_failed": ticket.level_ii_failed,
                "story_points": ticket.story_points,
                "project_key": ticket.ticket_key.split('-')[0] if ticket.ticket_key else None
            }
            ticket_list.append(ticket_data)
        
        response = {
            "tickets": ticket_list,
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
                "failed_testing_only": failed_testing_only
            }
        }
        
        return response
        
    except Exception as e:
        logger.error("Failed to get tickets", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get tickets: {str(e)}")


@router.get("/tickets/{ticket_key}", response_model=Dict[str, Any])
async def get_ticket_details(
    ticket_key: str,
    db: Session = Depends(get_db)
):
    """Get detailed information for a specific ticket"""
    try:
        ticket = db.query(JiraTicket).filter(JiraTicket.ticket_key == ticket_key).first()
        
        if not ticket:
            raise HTTPException(status_code=404, detail=f"Ticket {ticket_key} not found")
        
        # Get comments for this ticket
        comments = db.query(JiraComment).filter(JiraComment.ticket_id == ticket.id).all()
        
        ticket_details = {
            "ticket_key": ticket.ticket_key,
            "summary": ticket.summary,
            "description": ticket.description,
            "status": ticket.status,
            "priority": ticket.priority,
            "assignee": ticket.assignee,
            "reporter": ticket.reporter,
            "issue_type": ticket.issue_type,
            "created_date": ticket.created_date.isoformat() if ticket.created_date else None,
            "updated_date": ticket.updated_date.isoformat() if ticket.updated_date else None,
            "due_date": ticket.due_date.isoformat() if ticket.due_date else None,
            "resolution_date": ticket.resolution_date.isoformat() if ticket.resolution_date else None,
            "days_in_current_status": ticket.days_in_current_status,
            "is_stalled": ticket.is_stalled,
            "is_overdue": ticket.is_overdue,
            "level_ii_failed": ticket.level_ii_failed,
            "story_points": ticket.story_points,
            "project_key": ticket.ticket_key.split('-')[0] if ticket.ticket_key else None,
            "comments": [
                {
                    "comment_id": comment.comment_id,
                    "author": comment.author,
                    "body": comment.body,
                    "created_date": comment.created_date.isoformat() if comment.created_date else None,
                    "sentiment_score": comment.sentiment_score,
                    "contains_blocker": comment.contains_blocker,
                    "ai_summary": comment.ai_summary
                }
                for comment in comments
            ]
        }
        
        return ticket_details
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get ticket details", ticket_key=ticket_key, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get ticket details: {str(e)}")


@router.get("/analysis/stalled", response_model=Dict[str, Any])
async def get_stalled_tickets_analysis(
    days_back: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """Get comprehensive analysis of stalled tickets"""
    try:
        bi_service = BusinessIntelligenceService()
        analysis = await bi_service.analyze_stalled_tickets(days_back)
        await bi_service.close()
        
        return analysis
        
    except Exception as e:
        logger.error("Failed to analyze stalled tickets", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to analyze stalled tickets: {str(e)}")


@router.get("/analysis/overdue", response_model=Dict[str, Any])
async def get_overdue_analysis(
    days_back: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """Get analysis of overdue work"""
    try:
        bi_service = BusinessIntelligenceService()
        analysis = await bi_service.analyze_overdue_work(days_back)
        await bi_service.close()
        
        return analysis
        
    except Exception as e:
        logger.error("Failed to analyze overdue work", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to analyze overdue work: {str(e)}")


@router.get("/analysis/test-failures", response_model=Dict[str, Any])
async def get_test_failures_analysis(
    days_back: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """Get analysis of Level II test failures"""
    try:
        bi_service = BusinessIntelligenceService()
        analysis = await bi_service.analyze_level_ii_test_failures(days_back)
        await bi_service.close()
        
        return analysis
        
    except Exception as e:
        logger.error("Failed to analyze test failures", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to analyze test failures: {str(e)}")


@router.get("/search", response_model=Dict[str, Any])
async def search_tickets(
    query: str = Query(..., min_length=3, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Semantic search across JIRA tickets"""
    try:
        chroma_manager = ChromaDBManager()
        
        # Initialize ChromaDB if needed
        if not chroma_manager.client:
            await chroma_manager.initialize()
        
        # Perform semantic search
        search_results = await chroma_manager.semantic_search(
            query=query,
            collection_name="jira_tickets",
            limit=limit
        )
        
        await chroma_manager.close()
        
        return {
            "query": query,
            "results": search_results,
            "total_results": len(search_results)
        }
        
    except Exception as e:
        logger.error("Failed to search tickets", query=query, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to search tickets: {str(e)}")


@router.get("/similar/{ticket_key}", response_model=Dict[str, Any])
async def find_similar_tickets(
    ticket_key: str,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Find tickets similar to the specified ticket"""
    try:
        chroma_manager = ChromaDBManager()
        
        # Initialize ChromaDB if needed
        if not chroma_manager.client:
            await chroma_manager.initialize()
        
        # Find similar tickets
        similar_tickets = await chroma_manager.find_similar_issues(ticket_key, limit)
        
        await chroma_manager.close()
        
        return {
            "original_ticket": ticket_key,
            "similar_tickets": similar_tickets,
            "total_found": len(similar_tickets)
        }
        
    except Exception as e:
        logger.error("Failed to find similar tickets", ticket_key=ticket_key, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to find similar tickets: {str(e)}")


@router.get("/projects", response_model=List[Dict[str, Any]])
async def get_projects(
    db: Session = Depends(get_db)
):
    """Get all JIRA projects"""
    try:
        projects = db.query(JiraProject).all()
        
        project_list = []
        for project in projects:
            # Get ticket counts for each project
            ticket_count = db.query(JiraTicket).filter(
                JiraTicket.project_id == project.id
            ).count()
            
            stalled_count = db.query(JiraTicket).filter(
                and_(
                    JiraTicket.project_id == project.id,
                    JiraTicket.is_stalled == True
                )
            ).count()
            
            overdue_count = db.query(JiraTicket).filter(
                and_(
                    JiraTicket.project_id == project.id,
                    JiraTicket.is_overdue == True
                )
            ).count()
            
            project_data = {
                "project_key": project.project_key,
                "project_name": project.project_name,
                "project_type": project.project_type,
                "lead": project.lead,
                "description": project.description,
                "total_tickets": ticket_count,
                "stalled_tickets": stalled_count,
                "overdue_tickets": overdue_count,
                "health_score": max(10 - (stalled_count * 2) - (overdue_count * 3), 1)
            }
            project_list.append(project_data)
        
        # Sort by health score (worst first)
        project_list.sort(key=lambda x: x["health_score"])
        
        return project_list
        
    except Exception as e:
        logger.error("Failed to get projects", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get projects: {str(e)}")


@router.get("/statistics", response_model=Dict[str, Any])
async def get_jira_statistics(
    db: Session = Depends(get_db)
):
    """Get overall JIRA statistics"""
    try:
        # Get various counts
        total_tickets = db.query(JiraTicket).count()
        stalled_tickets = db.query(JiraTicket).filter(JiraTicket.is_stalled == True).count()
        overdue_tickets = db.query(JiraTicket).filter(JiraTicket.is_overdue == True).count()
        failed_tests = db.query(JiraTicket).filter(JiraTicket.level_ii_failed == True).count()
        
        # Get status distribution
        status_query = db.query(JiraTicket.status, db.func.count(JiraTicket.id)).group_by(JiraTicket.status).all()
        status_distribution = {status: count for status, count in status_query}
        
        # Get priority distribution
        priority_query = db.query(JiraTicket.priority, db.func.count(JiraTicket.id)).group_by(JiraTicket.priority).all()
        priority_distribution = {priority or 'None': count for priority, count in priority_query}
        
        # Get assignee distribution (top 10)
        assignee_query = db.query(JiraTicket.assignee, db.func.count(JiraTicket.id)).group_by(
            JiraTicket.assignee
        ).order_by(desc(db.func.count(JiraTicket.id))).limit(10).all()
        assignee_distribution = {assignee or 'Unassigned': count for assignee, count in assignee_query}
        
        statistics = {
            "overview": {
                "total_tickets": total_tickets,
                "stalled_tickets": stalled_tickets,
                "overdue_tickets": overdue_tickets,
                "failed_tests": failed_tests,
                "stalled_percentage": (stalled_tickets / total_tickets * 100) if total_tickets > 0 else 0,
                "overdue_percentage": (overdue_tickets / total_tickets * 100) if total_tickets > 0 else 0
            },
            "distributions": {
                "by_status": status_distribution,
                "by_priority": priority_distribution,
                "by_assignee": assignee_distribution
            },
            "timestamp": db.query(db.func.max(JiraTicket.updated_at)).scalar()
        }
        
        return statistics
        
    except Exception as e:
        logger.error("Failed to get JIRA statistics", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get JIRA statistics: {str(e)}")