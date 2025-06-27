"""
Confluence API endpoints for case reviews and deployment analysis
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from core.database import get_db
from models.confluence import ConfluencePage, CaseReview, DeploymentRecord
from services.business_intelligence import BusinessIntelligenceService
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/case-reviews", response_model=Dict[str, Any])
async def get_case_reviews(
    days_back: int = Query(30, ge=1, le=90, description="Number of days to look back"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get case reviews (standups) with pagination"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        query = db.query(CaseReview).filter(
            CaseReview.review_date >= cutoff_date
        )
        
        total_count = query.count()
        
        case_reviews = query.order_by(desc(CaseReview.review_date)).offset(offset).limit(limit).all()
        
        review_list = []
        for review in case_reviews:
            review_data = {
                "page_id": review.page_id,
                "review_date": review.review_date.isoformat() if review.review_date else None,
                "total_cases": review.total_cases,
                "critical_count": review.critical_count,
                "blocked_count": review.blocked_count,
                "stalled_count": review.stalled_count,
                "overdue_count": review.overdue_count,
                "critical_cases": review.critical_cases or [],
                "blocked_cases": review.blocked_cases or [],
                "high_urgency_cases": review.high_urgency_cases or [],
                "waiting_on_client_cases": review.waiting_on_client_cases or [],
                "internal_testing_cases": review.internal_testing_cases or [],
                "client_review_cases": review.client_review_cases or [],
                "prod_ready_cases": review.prod_ready_cases or [],
                "executive_summary": review.executive_summary,
                "key_blockers": review.key_blockers or [],
                "negative_sentiment_items": review.negative_sentiment_items or [],
                "recommendations": review.recommendations
            }
            review_list.append(review_data)
        
        response = {
            "case_reviews": review_list,
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "summary": {
                "total_reviews": total_count,
                "date_range": {
                    "start": cutoff_date.isoformat(),
                    "end": datetime.utcnow().isoformat()
                }
            }
        }
        
        return response
        
    except Exception as e:
        logger.error("Failed to get case reviews", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get case reviews: {str(e)}")


@router.get("/case-reviews/{page_id}", response_model=Dict[str, Any])
async def get_case_review_details(
    page_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed information for a specific case review"""
    try:
        case_review = db.query(CaseReview).filter(CaseReview.page_id == page_id).first()
        
        if not case_review:
            raise HTTPException(status_code=404, detail=f"Case review {page_id} not found")
        
        review_details = {
            "page_id": case_review.page_id,
            "review_date": case_review.review_date.isoformat() if case_review.review_date else None,
            "total_cases": case_review.total_cases,
            "critical_count": case_review.critical_count,
            "blocked_count": case_review.blocked_count,
            "stalled_count": case_review.stalled_count,
            "overdue_count": case_review.overdue_count,
            "sections": {
                "critical_cases": case_review.critical_cases or [],
                "high_urgency_cases": case_review.high_urgency_cases or [],
                "blocked_cases": case_review.blocked_cases or [],
                "waiting_on_client_cases": case_review.waiting_on_client_cases or [],
                "internal_testing_cases": case_review.internal_testing_cases or [],
                "client_review_cases": case_review.client_review_cases or [],
                "prod_ready_cases": case_review.prod_ready_cases or []
            },
            "analysis": {
                "executive_summary": case_review.executive_summary,
                "key_blockers": case_review.key_blockers or [],
                "negative_sentiment_items": case_review.negative_sentiment_items or [],
                "recommendations": case_review.recommendations
            },
            "created_at": case_review.created_at.isoformat() if case_review.created_at else None,
            "updated_at": case_review.updated_at.isoformat() if case_review.updated_at else None
        }
        
        return review_details
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get case review details", page_id=page_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get case review details: {str(e)}")


@router.get("/deployments", response_model=Dict[str, Any])
async def get_deployments(
    days_back: int = Query(30, ge=1, le=90),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    failed_only: bool = Query(False, description="Show only failed deployments"),
    db: Session = Depends(get_db)
):
    """Get deployment records with filtering"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        query = db.query(DeploymentRecord).filter(
            DeploymentRecord.deployment_date >= cutoff_date
        )
        
        if failed_only:
            query = query.filter(DeploymentRecord.has_failures == True)
        
        total_count = query.count()
        
        deployments = query.order_by(desc(DeploymentRecord.deployment_date)).offset(offset).limit(limit).all()
        
        deployment_list = []
        for deployment in deployments:
            deployment_data = {
                "page_id": deployment.page_id,
                "deployment_date": deployment.deployment_date.isoformat() if deployment.deployment_date else None,
                "cases": deployment.cases or [],
                "has_failures": deployment.has_failures,
                "failure_details": deployment.failure_details or [],
                "deployment_status": deployment.deployment_status,
                "client_project": deployment.client_project,
                "success_rate": deployment.success_rate,
                "ai_summary": deployment.ai_summary,
                "case_count": len(deployment.cases) if deployment.cases else 0,
                "failure_count": len(deployment.failure_details) if deployment.failure_details else 0
            }
            deployment_list.append(deployment_data)
        
        # Calculate summary statistics
        total_deployments = len(deployment_list)
        failed_deployments = sum(1 for d in deployment_list if d["has_failures"])
        success_rate = ((total_deployments - failed_deployments) / total_deployments * 100) if total_deployments > 0 else 100
        
        response = {
            "deployments": deployment_list,
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "summary": {
                "total_deployments": total_deployments,
                "failed_deployments": failed_deployments,
                "success_rate": success_rate,
                "date_range": {
                    "start": cutoff_date.isoformat(),
                    "end": datetime.utcnow().isoformat()
                }
            },
            "filters_applied": {
                "days_back": days_back,
                "failed_only": failed_only
            }
        }
        
        return response
        
    except Exception as e:
        logger.error("Failed to get deployments", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get deployments: {str(e)}")


@router.get("/deployments/analysis", response_model=Dict[str, Any])
async def get_deployment_analysis(
    days_back: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """Get comprehensive deployment analysis"""
    try:
        bi_service = BusinessIntelligenceService()
        analysis = await bi_service.analyze_failed_deployments(days_back)
        await bi_service.close()
        
        return analysis
        
    except Exception as e:
        logger.error("Failed to analyze deployments", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to analyze deployments: {str(e)}")


@router.get("/case-reviews/analysis", response_model=Dict[str, Any])
async def analyze_case_reviews(
    days_back: int = Query(14, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """Get analysis and trends from case reviews"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        case_reviews = db.query(CaseReview).filter(
            CaseReview.review_date >= cutoff_date
        ).order_by(CaseReview.review_date).all()
        
        if not case_reviews:
            return {"message": "No case reviews found for the specified period", "analysis": {}}
        
        # Calculate trends
        total_cases_trend = [review.total_cases for review in case_reviews]
        critical_cases_trend = [review.critical_count for review in case_reviews]
        blocked_cases_trend = [review.blocked_count for review in case_reviews]
        
        # Calculate averages
        avg_total_cases = sum(total_cases_trend) / len(total_cases_trend)
        avg_critical_cases = sum(critical_cases_trend) / len(critical_cases_trend)
        avg_blocked_cases = sum(blocked_cases_trend) / len(blocked_cases_trend)
        
        # Identify most common blockers
        all_blockers = []
        for review in case_reviews:
            if review.key_blockers:
                all_blockers.extend(review.key_blockers)
        
        # Count blocker frequency (simplified)
        blocker_frequency = {}
        for blocker in all_blockers:
            if isinstance(blocker, str):
                blocker_frequency[blocker] = blocker_frequency.get(blocker, 0) + 1
        
        # Get most recent review for current status
        latest_review = case_reviews[-1] if case_reviews else None
        
        analysis = {
            "period_days": days_back,
            "total_reviews": len(case_reviews),
            "trends": {
                "total_cases": {
                    "average": avg_total_cases,
                    "trend_data": total_cases_trend,
                    "current": latest_review.total_cases if latest_review else 0
                },
                "critical_cases": {
                    "average": avg_critical_cases,
                    "trend_data": critical_cases_trend,
                    "current": latest_review.critical_count if latest_review else 0
                },
                "blocked_cases": {
                    "average": avg_blocked_cases,
                    "trend_data": blocked_cases_trend,
                    "current": latest_review.blocked_count if latest_review else 0
                }
            },
            "common_blockers": dict(sorted(blocker_frequency.items(), key=lambda x: x[1], reverse=True)[:10]),
            "latest_status": {
                "review_date": latest_review.review_date.isoformat() if latest_review and latest_review.review_date else None,
                "total_cases": latest_review.total_cases if latest_review else 0,
                "critical_count": latest_review.critical_count if latest_review else 0,
                "blocked_count": latest_review.blocked_count if latest_review else 0,
                "executive_summary": latest_review.executive_summary if latest_review else None
            },
            "recommendations": _generate_case_review_recommendations(case_reviews),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return analysis
        
    except Exception as e:
        logger.error("Failed to analyze case reviews", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to analyze case reviews: {str(e)}")


@router.get("/pages", response_model=Dict[str, Any])
async def get_confluence_pages(
    space_key: Optional[str] = Query(None, description="Filter by space key"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get Confluence pages with filtering"""
    try:
        query = db.query(ConfluencePage)
        
        if space_key:
            query = query.filter(ConfluencePage.space_key == space_key)
        
        total_count = query.count()
        
        pages = query.order_by(desc(ConfluencePage.updated_date)).offset(offset).limit(limit).all()
        
        page_list = []
        for page in pages:
            page_data = {
                "page_id": page.page_id,
                "space_key": page.space_key,
                "title": page.title,
                "content_type": page.content_type,
                "author": page.author,
                "created_date": page.created_date.isoformat() if page.created_date else None,
                "updated_date": page.updated_date.isoformat() if page.updated_date else None,
                "version": page.version,
                "parent_id": page.parent_id,
                "content_preview": page.content[:200] + "..." if page.content and len(page.content) > 200 else page.content
            }
            page_list.append(page_data)
        
        response = {
            "pages": page_list,
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "filters_applied": {
                "space_key": space_key
            }
        }
        
        return response
        
    except Exception as e:
        logger.error("Failed to get Confluence pages", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get Confluence pages: {str(e)}")


@router.get("/statistics", response_model=Dict[str, Any])
async def get_confluence_statistics(
    db: Session = Depends(get_db)
):
    """Get overall Confluence statistics"""
    try:
        # Count case reviews
        total_case_reviews = db.query(CaseReview).count()
        recent_case_reviews = db.query(CaseReview).filter(
            CaseReview.review_date >= datetime.utcnow() - timedelta(days=30)
        ).count()
        
        # Count deployments
        total_deployments = db.query(DeploymentRecord).count()
        recent_deployments = db.query(DeploymentRecord).filter(
            DeploymentRecord.deployment_date >= datetime.utcnow() - timedelta(days=30)
        ).count()
        
        failed_deployments = db.query(DeploymentRecord).filter(
            DeploymentRecord.has_failures == True,
            DeploymentRecord.deployment_date >= datetime.utcnow() - timedelta(days=30)
        ).count()
        
        # Count pages
        total_pages = db.query(ConfluencePage).count()
        
        # Calculate success rates
        deployment_success_rate = ((recent_deployments - failed_deployments) / recent_deployments * 100) if recent_deployments > 0 else 100
        
        statistics = {
            "case_reviews": {
                "total": total_case_reviews,
                "recent_30_days": recent_case_reviews
            },
            "deployments": {
                "total": total_deployments,
                "recent_30_days": recent_deployments,
                "failed_30_days": failed_deployments,
                "success_rate_30_days": deployment_success_rate
            },
            "pages": {
                "total": total_pages
            },
            "last_updated": datetime.utcnow().isoformat()
        }
        
        return statistics
        
    except Exception as e:
        logger.error("Failed to get Confluence statistics", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get Confluence statistics: {str(e)}")


# Helper functions

def _generate_case_review_recommendations(case_reviews: List[CaseReview]) -> List[str]:
    """Generate recommendations based on case review analysis"""
    recommendations = []
    
    if not case_reviews:
        return recommendations
    
    latest_review = case_reviews[-1]
    
    # High number of blocked cases
    if latest_review.blocked_count > 5:
        recommendations.append("High number of blocked cases - review resource allocation and dependencies")
    
    # High number of critical cases
    if latest_review.critical_count > 8:
        recommendations.append("Many critical cases active - consider emergency resource reallocation")
    
    # Trend analysis
    if len(case_reviews) > 1:
        prev_review = case_reviews[-2]
        
        # Increasing blocked cases
        if latest_review.blocked_count > prev_review.blocked_count:
            recommendations.append("Blocked cases trending upward - identify and resolve systemic blockers")
        
        # Increasing critical cases
        if latest_review.critical_count > prev_review.critical_count:
            recommendations.append("Critical cases increasing - prioritize and escalate resolution")
    
    if not recommendations:
        recommendations.append("Overall case flow appears healthy - continue monitoring")
    
    return recommendations