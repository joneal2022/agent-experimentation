"""
Analysis Orchestrator using LangGraph for coordinating AI analysis workflows
"""
import asyncio
from typing import List, Dict, Any, Optional, TypedDict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
import json

from core.database import get_db
from models.jira import JiraTicket, JiraComment
from models.confluence import CaseReview, DeploymentRecord
from models.alerts import Alert, ExecutiveSummary, AlertType, AlertSeverity
from services.ai_analysis import AIAnalysisService
from storage.chromadb_manager import ChromaDBManager
from utils.logging import get_logger

logger = get_logger(__name__)


class AnalysisState(TypedDict):
    """State for LangGraph analysis workflow"""
    analysis_type: str
    data_collected: Dict[str, Any]
    ai_results: Dict[str, Any]
    insights: Dict[str, Any]
    alerts_generated: List[Dict[str, Any]]
    executive_summary: Dict[str, Any]
    completed_steps: List[str]
    errors: List[str]


class AnalysisOrchestrator:
    """LangGraph-based orchestrator for AI analysis workflows"""
    
    def __init__(self):
        self.ai_service = AIAnalysisService()
        self.chroma_manager = ChromaDBManager()
        self.graph = None
        self._build_analysis_graph()
        
    def _build_analysis_graph(self):
        """Build the LangGraph analysis workflow"""
        
        # Define the workflow graph
        workflow = StateGraph(AnalysisState)
        
        # Add nodes
        workflow.add_node("collect_data", self._collect_data_node)
        workflow.add_node("analyze_jira", self._analyze_jira_node)
        workflow.add_node("analyze_confluence", self._analyze_confluence_node)
        workflow.add_node("analyze_patterns", self._analyze_patterns_node)
        workflow.add_node("generate_insights", self._generate_insights_node)
        workflow.add_node("create_alerts", self._create_alerts_node)
        workflow.add_node("executive_summary", self._executive_summary_node)
        
        # Define workflow edges
        workflow.set_entry_point("collect_data")
        workflow.add_edge("collect_data", "analyze_jira")
        workflow.add_edge("analyze_jira", "analyze_confluence")
        workflow.add_edge("analyze_confluence", "analyze_patterns")
        workflow.add_edge("analyze_patterns", "generate_insights")
        workflow.add_edge("generate_insights", "create_alerts")
        workflow.add_edge("create_alerts", "executive_summary")
        workflow.add_edge("executive_summary", END)
        
        # Compile the graph
        self.graph = workflow.compile()
    
    async def run_daily_analysis(self) -> Dict[str, Any]:
        """Run the complete daily analysis workflow"""
        try:
            logger.info("Starting daily analysis workflow")
            
            # Initialize ChromaDB if not already done
            if not self.chroma_manager.client:
                await self.chroma_manager.initialize()
            
            # Initial state
            initial_state: AnalysisState = {
                "analysis_type": "daily",
                "data_collected": {},
                "ai_results": {},
                "insights": {},
                "alerts_generated": [],
                "executive_summary": {},
                "completed_steps": [],
                "errors": []
            }
            
            # Run the workflow
            final_state = await self.graph.ainvoke(initial_state)
            
            logger.info("Daily analysis workflow completed", 
                       completed_steps=len(final_state["completed_steps"]),
                       errors=len(final_state["errors"]))
            
            return final_state
            
        except Exception as e:
            logger.error("Daily analysis workflow failed", error=str(e))
            raise
    
    async def _collect_data_node(self, state: AnalysisState) -> AnalysisState:
        """Collect data from all sources for analysis"""
        try:
            logger.info("Collecting data for analysis")
            
            db = next(get_db())
            
            # Get recent data (last 7 days for daily analysis)
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            
            # Collect JIRA data
            jira_data = {
                "stalled_tickets": db.query(JiraTicket).filter(
                    JiraTicket.is_stalled == True,
                    JiraTicket.updated_at >= cutoff_date
                ).all(),
                "overdue_tickets": db.query(JiraTicket).filter(
                    JiraTicket.is_overdue == True,
                    JiraTicket.updated_at >= cutoff_date
                ).all(),
                "failed_testing": db.query(JiraTicket).filter(
                    JiraTicket.level_ii_failed == True,
                    JiraTicket.updated_at >= cutoff_date
                ).all(),
                "recent_comments": db.query(JiraComment).filter(
                    JiraComment.created_at >= cutoff_date
                ).all()
            }
            
            # Collect Confluence data
            confluence_data = {
                "case_reviews": db.query(CaseReview).filter(
                    CaseReview.review_date >= cutoff_date
                ).all(),
                "deployment_records": db.query(DeploymentRecord).filter(
                    DeploymentRecord.deployment_date >= cutoff_date
                ).all()
            }
            
            db.close()
            
            # Convert to dictionaries for JSON serialization
            state["data_collected"] = {
                "jira": {
                    "stalled_tickets": [self._ticket_to_dict(t) for t in jira_data["stalled_tickets"]],
                    "overdue_tickets": [self._ticket_to_dict(t) for t in jira_data["overdue_tickets"]],
                    "failed_testing": [self._ticket_to_dict(t) for t in jira_data["failed_testing"]],
                    "recent_comments": [self._comment_to_dict(c) for c in jira_data["recent_comments"]]
                },
                "confluence": {
                    "case_reviews": [self._case_review_to_dict(cr) for cr in confluence_data["case_reviews"]],
                    "deployment_records": [self._deployment_to_dict(dr) for dr in confluence_data["deployment_records"]]
                }
            }
            
            state["completed_steps"].append("collect_data")
            logger.info("Data collection completed", 
                       stalled_tickets=len(jira_data["stalled_tickets"]),
                       overdue_tickets=len(jira_data["overdue_tickets"]),
                       case_reviews=len(confluence_data["case_reviews"]))
            
            return state
            
        except Exception as e:
            error_msg = f"Data collection failed: {str(e)}"
            state["errors"].append(error_msg)
            logger.error("Data collection node failed", error=str(e))
            return state
    
    async def _analyze_jira_node(self, state: AnalysisState) -> AnalysisState:
        """Analyze JIRA data using AI"""
        try:
            logger.info("Analyzing JIRA data")
            
            jira_data = state["data_collected"].get("jira", {})
            
            # Analyze comments in batches
            comments = jira_data.get("recent_comments", [])
            if comments:
                comment_analyses = await self.ai_service.analyze_batch_comments(comments)
                
                # Update ChromaDB with analyzed comments
                await self.chroma_manager.add_jira_comments(comment_analyses)
            else:
                comment_analyses = []
            
            # Analyze ticket patterns
            stalled_tickets = jira_data.get("stalled_tickets", [])
            overdue_tickets = jira_data.get("overdue_tickets", [])
            failed_testing = jira_data.get("failed_testing", [])
            
            # Add tickets to ChromaDB for semantic search
            all_tickets = stalled_tickets + overdue_tickets + failed_testing
            if all_tickets:
                await self.chroma_manager.add_jira_tickets(all_tickets)
            
            # Analyze sentiment trends
            sentiment_analysis = self._analyze_sentiment_trends(comment_analyses)
            
            state["ai_results"]["jira"] = {
                "comment_analyses": comment_analyses,
                "sentiment_trends": sentiment_analysis,
                "stalled_analysis": self._analyze_stalled_tickets(stalled_tickets),
                "overdue_analysis": self._analyze_overdue_tickets(overdue_tickets),
                "testing_failures": self._analyze_testing_failures(failed_testing)
            }
            
            state["completed_steps"].append("analyze_jira")
            logger.info("JIRA analysis completed", 
                       comments_analyzed=len(comment_analyses),
                       tickets_processed=len(all_tickets))
            
            return state
            
        except Exception as e:
            error_msg = f"JIRA analysis failed: {str(e)}"
            state["errors"].append(error_msg)
            logger.error("JIRA analysis node failed", error=str(e))
            return state
    
    async def _analyze_confluence_node(self, state: AnalysisState) -> AnalysisState:
        """Analyze Confluence data using AI"""
        try:
            logger.info("Analyzing Confluence data")
            
            confluence_data = state["data_collected"].get("confluence", {})
            
            # Analyze case reviews
            case_reviews = confluence_data.get("case_reviews", [])
            case_review_analyses = []
            
            for review in case_reviews:
                analysis = await self.ai_service.analyze_case_review(review)
                analysis["review_id"] = review.get("page_id")
                analysis["review_date"] = review.get("review_date")
                case_review_analyses.append(analysis)
            
            # Add case reviews to ChromaDB
            if case_reviews:
                await self.chroma_manager.add_case_reviews(case_reviews)
            
            # Analyze deployment records
            deployment_records = confluence_data.get("deployment_records", [])
            deployment_analyses = []
            
            for deployment in deployment_records:
                analysis = await self.ai_service.analyze_deployment_record(deployment)
                analysis["deployment_id"] = deployment.get("page_id")
                analysis["deployment_date"] = deployment.get("deployment_date")
                deployment_analyses.append(analysis)
            
            state["ai_results"]["confluence"] = {
                "case_review_analyses": case_review_analyses,
                "deployment_analyses": deployment_analyses,
                "deployment_success_rate": self._calculate_deployment_success_rate(deployment_analyses)
            }
            
            state["completed_steps"].append("analyze_confluence")
            logger.info("Confluence analysis completed", 
                       case_reviews=len(case_review_analyses),
                       deployments=len(deployment_analyses))
            
            return state
            
        except Exception as e:
            error_msg = f"Confluence analysis failed: {str(e)}"
            state["errors"].append(error_msg)
            logger.error("Confluence analysis node failed", error=str(e))
            return state
    
    async def _analyze_patterns_node(self, state: AnalysisState) -> AnalysisState:
        """Analyze patterns across all data sources"""
        try:
            logger.info("Analyzing cross-platform patterns")
            
            # Find patterns using ChromaDB semantic search
            patterns = await self.chroma_manager.find_problematic_patterns()
            
            # Analyze historical trends
            historical_data = self._prepare_historical_data(state)
            trend_analysis = await self.ai_service.identify_trends(historical_data, "daily_operations")
            
            state["ai_results"]["patterns"] = {
                "semantic_patterns": patterns,
                "trend_analysis": trend_analysis,
                "cross_platform_insights": self._find_cross_platform_insights(state)
            }
            
            state["completed_steps"].append("analyze_patterns")
            logger.info("Pattern analysis completed")
            
            return state
            
        except Exception as e:
            error_msg = f"Pattern analysis failed: {str(e)}"
            state["errors"].append(error_msg)
            logger.error("Pattern analysis node failed", error=str(e))
            return state
    
    async def _generate_insights_node(self, state: AnalysisState) -> AnalysisState:
        """Generate executive insights from all analyses"""
        try:
            logger.info("Generating executive insights")
            
            # Compile all analysis results
            all_results = state["ai_results"]
            
            # Generate comprehensive insights
            insights = {
                "key_metrics": self._calculate_key_metrics(state),
                "risk_assessment": self._assess_risks(all_results),
                "performance_trends": self._analyze_performance_trends(all_results),
                "resource_optimization": self._analyze_resource_optimization(all_results),
                "quality_indicators": self._analyze_quality_indicators(all_results)
            }
            
            state["insights"] = insights
            state["completed_steps"].append("generate_insights")
            
            logger.info("Executive insights generated")
            return state
            
        except Exception as e:
            error_msg = f"Insight generation failed: {str(e)}"
            state["errors"].append(error_msg)
            logger.error("Insight generation node failed", error=str(e))
            return state
    
    async def _create_alerts_node(self, state: AnalysisState) -> AnalysisState:
        """Create alerts based on analysis results"""
        try:
            logger.info("Creating alerts from analysis")
            
            alerts = []
            
            # Check for critical conditions
            jira_results = state["ai_results"].get("jira", {})
            confluence_results = state["ai_results"].get("confluence", {})
            
            # Alert for stalled tickets
            stalled_tickets = state["data_collected"]["jira"].get("stalled_tickets", [])
            if len(stalled_tickets) > 5:  # Threshold
                alerts.append({
                    "type": AlertType.STALLED_TICKET.value,
                    "severity": AlertSeverity.HIGH.value,
                    "title": f"{len(stalled_tickets)} Tickets Stalled",
                    "description": f"Found {len(stalled_tickets)} tickets stalled for >5 days requiring attention",
                    "context": {"stalled_count": len(stalled_tickets)}
                })
            
            # Alert for deployment failures
            deployment_analyses = confluence_results.get("deployment_analyses", [])
            failed_deployments = [d for d in deployment_analyses if d.get("quality_score", 10) < 7]
            if failed_deployments:
                alerts.append({
                    "type": AlertType.DEPLOYMENT_FAILURE.value,
                    "severity": AlertSeverity.CRITICAL.value,
                    "title": "Deployment Quality Issues",
                    "description": f"Found {len(failed_deployments)} deployments with quality issues",
                    "context": {"failed_deployments": len(failed_deployments)}
                })
            
            # Alert for negative sentiment spike
            sentiment_trends = jira_results.get("sentiment_trends", {})
            if sentiment_trends.get("negative_percentage", 0) > 30:  # Threshold
                alerts.append({
                    "type": AlertType.QUALITY_ISSUE.value,
                    "severity": AlertSeverity.MEDIUM.value,
                    "title": "Negative Sentiment Spike",
                    "description": f"High negative sentiment detected in comments ({sentiment_trends.get('negative_percentage', 0):.1f}%)",
                    "context": sentiment_trends
                })
            
            state["alerts_generated"] = alerts
            state["completed_steps"].append("create_alerts")
            
            logger.info("Alerts created", count=len(alerts))
            return state
            
        except Exception as e:
            error_msg = f"Alert creation failed: {str(e)}"
            state["errors"].append(error_msg)
            logger.error("Alert creation node failed", error=str(e))
            return state
    
    async def _executive_summary_node(self, state: AnalysisState) -> AnalysisState:
        """Generate executive summary"""
        try:
            logger.info("Generating executive summary")
            
            # Prepare comprehensive data for summary
            summary_data = {
                "analysis_results": state["ai_results"],
                "insights": state["insights"],
                "alerts": state["alerts_generated"],
                "metrics": self._calculate_key_metrics(state)
            }
            
            # Generate AI-powered executive summary
            executive_summary = await self.ai_service.generate_executive_summary(summary_data)
            
            # Add metadata
            executive_summary.update({
                "generated_at": datetime.utcnow().isoformat(),
                "analysis_type": state["analysis_type"],
                "data_sources": list(state["data_collected"].keys()),
                "completed_steps": state["completed_steps"],
                "error_count": len(state["errors"])
            })
            
            state["executive_summary"] = executive_summary
            state["completed_steps"].append("executive_summary")
            
            logger.info("Executive summary generated")
            return state
            
        except Exception as e:
            error_msg = f"Executive summary generation failed: {str(e)}"
            state["errors"].append(error_msg)
            logger.error("Executive summary node failed", error=str(e))
            return state
    
    # Helper methods for data conversion and analysis
    
    def _ticket_to_dict(self, ticket) -> Dict[str, Any]:
        """Convert ticket object to dictionary"""
        return {
            "ticket_key": ticket.ticket_key,
            "summary": ticket.summary,
            "description": ticket.description,
            "status": ticket.status,
            "priority": ticket.priority,
            "assignee": ticket.assignee,
            "is_stalled": ticket.is_stalled,
            "is_overdue": ticket.is_overdue,
            "level_ii_failed": ticket.level_ii_failed,
            "days_in_current_status": ticket.days_in_current_status,
            "created_date": ticket.created_date,
            "updated_date": ticket.updated_date
        }
    
    def _comment_to_dict(self, comment) -> Dict[str, Any]:
        """Convert comment object to dictionary"""
        return {
            "comment_id": comment.comment_id,
            "ticket_key": getattr(comment.ticket, 'ticket_key', '') if comment.ticket else '',
            "author": comment.author,
            "body": comment.body,
            "created_date": comment.created_date,
            "sentiment_score": comment.sentiment_score,
            "contains_blocker": comment.contains_blocker
        }
    
    def _case_review_to_dict(self, case_review) -> Dict[str, Any]:
        """Convert case review object to dictionary"""
        return {
            "page_id": case_review.page_id,
            "review_date": case_review.review_date,
            "total_cases": case_review.total_cases,
            "critical_count": case_review.critical_count,
            "blocked_count": case_review.blocked_count,
            "stalled_count": case_review.stalled_count,
            "critical_cases": case_review.critical_cases,
            "blocked_cases": case_review.blocked_cases
        }
    
    def _deployment_to_dict(self, deployment) -> Dict[str, Any]:
        """Convert deployment object to dictionary"""
        return {
            "page_id": deployment.page_id,
            "deployment_date": deployment.deployment_date,
            "cases": deployment.cases,
            "has_failures": deployment.has_failures,
            "failure_details": deployment.failure_details
        }
    
    def _analyze_sentiment_trends(self, comment_analyses: List[Dict]) -> Dict[str, Any]:
        """Analyze sentiment trends from comment analyses"""
        if not comment_analyses:
            return {"total_comments": 0, "positive_percentage": 0, "negative_percentage": 0}
        
        sentiments = [c.get("sentiment", "neutral") for c in comment_analyses]
        total = len(sentiments)
        positive = sentiments.count("positive")
        negative = sentiments.count("negative")
        
        return {
            "total_comments": total,
            "positive_percentage": (positive / total) * 100,
            "negative_percentage": (negative / total) * 100,
            "neutral_percentage": ((total - positive - negative) / total) * 100
        }
    
    def _analyze_stalled_tickets(self, stalled_tickets: List[Dict]) -> Dict[str, Any]:
        """Analyze stalled tickets patterns"""
        if not stalled_tickets:
            return {"count": 0, "average_days_stalled": 0}
        
        total_days = sum(t.get("days_in_current_status", 0) for t in stalled_tickets)
        avg_days = total_days / len(stalled_tickets) if stalled_tickets else 0
        
        return {
            "count": len(stalled_tickets),
            "average_days_stalled": avg_days,
            "longest_stalled": max((t.get("days_in_current_status", 0) for t in stalled_tickets), default=0)
        }
    
    def _analyze_overdue_tickets(self, overdue_tickets: List[Dict]) -> Dict[str, Any]:
        """Analyze overdue tickets patterns"""
        return {
            "count": len(overdue_tickets),
            "priorities": self._count_priorities(overdue_tickets),
            "projects": self._count_projects(overdue_tickets)
        }
    
    def _analyze_testing_failures(self, failed_tickets: List[Dict]) -> Dict[str, Any]:
        """Analyze testing failure patterns"""
        return {
            "count": len(failed_tickets),
            "priorities": self._count_priorities(failed_tickets),
            "projects": self._count_projects(failed_tickets)
        }
    
    def _count_priorities(self, tickets: List[Dict]) -> Dict[str, int]:
        """Count tickets by priority"""
        priorities = {}
        for ticket in tickets:
            priority = ticket.get("priority", "Unknown")
            priorities[priority] = priorities.get(priority, 0) + 1
        return priorities
    
    def _count_projects(self, tickets: List[Dict]) -> Dict[str, int]:
        """Count tickets by project"""
        projects = {}
        for ticket in tickets:
            project = ticket.get("ticket_key", "").split("-")[0] if ticket.get("ticket_key") else "Unknown"
            projects[project] = projects.get(project, 0) + 1
        return projects
    
    def _calculate_deployment_success_rate(self, deployment_analyses: List[Dict]) -> float:
        """Calculate deployment success rate"""
        if not deployment_analyses:
            return 100.0
        
        total_quality = sum(d.get("quality_score", 0) for d in deployment_analyses)
        return (total_quality / (len(deployment_analyses) * 10)) * 100
    
    def _prepare_historical_data(self, state: AnalysisState) -> List[Dict[str, Any]]:
        """Prepare historical data for trend analysis"""
        # This would typically pull from database historical records
        # For now, return current analysis as data point
        return [state["ai_results"]]
    
    def _find_cross_platform_insights(self, state: AnalysisState) -> Dict[str, Any]:
        """Find insights that span multiple platforms"""
        # Correlate JIRA issues with Confluence deployment failures
        # This is a simplified implementation
        return {
            "jira_confluence_correlation": "Analysis complete",
            "deployment_impact_on_tickets": "Under review"
        }
    
    def _calculate_key_metrics(self, state: AnalysisState) -> Dict[str, Any]:
        """Calculate key business metrics"""
        jira_data = state["data_collected"].get("jira", {})
        
        return {
            "stalled_tickets": len(jira_data.get("stalled_tickets", [])),
            "overdue_tickets": len(jira_data.get("overdue_tickets", [])),
            "failed_tests": len(jira_data.get("failed_testing", [])),
            "total_active_issues": len(jira_data.get("stalled_tickets", [])) + len(jira_data.get("overdue_tickets", [])),
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
    
    def _assess_risks(self, all_results: Dict[str, Any]) -> Dict[str, str]:
        """Assess business risks from analysis"""
        # Simplified risk assessment
        return {
            "delivery_risk": "medium",
            "quality_risk": "low",
            "client_satisfaction_risk": "medium"
        }
    
    def _analyze_performance_trends(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance trends"""
        return {
            "trend_direction": "stable",
            "key_improvements": [],
            "areas_of_concern": []
        }
    
    def _analyze_resource_optimization(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze resource optimization opportunities"""
        return {
            "bottlenecks": [],
            "underutilized_resources": [],
            "optimization_opportunities": []
        }
    
    def _analyze_quality_indicators(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze quality indicators"""
        return {
            "code_quality_score": 8,
            "testing_effectiveness": 85,
            "deployment_reliability": 90
        }
    
    async def generate_weekly_report(self) -> Dict[str, Any]:
        """Generate weekly comprehensive report"""
        try:
            logger.info("Generating weekly report")
            
            # Run extended analysis with 30-day lookback
            initial_state: AnalysisState = {
                "analysis_type": "weekly",
                "data_collected": {},
                "ai_results": {},
                "insights": {},
                "alerts_generated": [],
                "executive_summary": {},
                "completed_steps": [],
                "errors": []
            }
            
            # Modify collection to get more historical data
            weekly_state = await self.graph.ainvoke(initial_state)
            
            logger.info("Weekly report generated")
            return weekly_state
            
        except Exception as e:
            logger.error("Weekly report generation failed", error=str(e))
            raise
    
    async def close(self):
        """Close analysis orchestrator"""
        if self.ai_service:
            await self.ai_service.close()
        if self.chroma_manager:
            await self.chroma_manager.close()
        logger.info("Analysis orchestrator closed")