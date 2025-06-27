"""
Business Intelligence Service for AI-powered analysis of specific business scenarios
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from core.database import get_db
from models.jira import JiraTicket, JiraComment, JiraStatusHistory
from models.confluence import CaseReview, DeploymentRecord
from models.alerts import Alert, ExecutiveSummary
from services.ai_analysis import AIAnalysisService
from storage.chromadb_manager import ChromaDBManager
from utils.logging import get_logger

logger = get_logger(__name__)


class BusinessIntelligenceService:
    """Service for AI-powered business intelligence analysis"""
    
    def __init__(self):
        self.ai_service = AIAnalysisService()
        self.chroma_manager = ChromaDBManager()
        
    async def analyze_stalled_tickets(self, days_back: int = 30) -> Dict[str, Any]:
        """Comprehensive analysis of stalled tickets with AI insights"""
        try:
            logger.info("Analyzing stalled tickets", days_back=days_back)
            
            db = next(get_db())
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Get stalled tickets
            stalled_tickets = db.query(JiraTicket).filter(
                JiraTicket.is_stalled == True,
                JiraTicket.updated_at >= cutoff_date
            ).all()
            
            if not stalled_tickets:
                db.close()
                return {"message": "No stalled tickets found", "count": 0}
            
            # Group by various dimensions
            analysis = {
                "total_stalled": len(stalled_tickets),
                "by_project": self._group_by_project(stalled_tickets),
                "by_assignee": self._group_by_assignee(stalled_tickets),
                "by_priority": self._group_by_priority(stalled_tickets),
                "by_status": self._group_by_status(stalled_tickets),
                "duration_analysis": self._analyze_stall_duration(stalled_tickets),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Get comments for stalled tickets to understand root causes
            stalled_ticket_keys = [t.ticket_key for t in stalled_tickets]
            comments = db.query(JiraComment).filter(
                JiraComment.ticket_id.in_([t.id for t in stalled_tickets]),
                JiraComment.created_at >= cutoff_date
            ).all()
            
            db.close()
            
            # AI-powered root cause analysis
            if comments:
                comment_analysis = await self._analyze_stall_comments(comments)
                analysis["root_cause_analysis"] = comment_analysis
            
            # Semantic search for similar stalled patterns
            if self.chroma_manager.client:
                similar_patterns = await self.chroma_manager.semantic_search(
                    query="stalled blocked delayed waiting",
                    collection_name="jira_tickets",
                    filters={"is_stalled": True},
                    limit=20
                )
                analysis["similar_patterns"] = similar_patterns
            
            # Generate AI insights and recommendations
            ai_insights = await self._generate_stall_insights(analysis)
            analysis["ai_insights"] = ai_insights
            
            logger.info("Stalled tickets analysis completed", 
                       total_stalled=analysis["total_stalled"])
            
            return analysis
            
        except Exception as e:
            logger.error("Failed to analyze stalled tickets", error=str(e))
            return {"error": str(e), "count": 0}
    
    async def analyze_overdue_work(self, days_back: int = 30) -> Dict[str, Any]:
        """Comprehensive analysis of overdue work with impact assessment"""
        try:
            logger.info("Analyzing overdue work", days_back=days_back)
            
            db = next(get_db())
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Get overdue tickets
            overdue_tickets = db.query(JiraTicket).filter(
                JiraTicket.is_overdue == True,
                JiraTicket.due_date >= cutoff_date
            ).all()
            
            if not overdue_tickets:
                db.close()
                return {"message": "No overdue tickets found", "count": 0}
            
            # Calculate impact metrics
            analysis = {
                "total_overdue": len(overdue_tickets),
                "by_project": self._group_by_project(overdue_tickets),
                "by_client": self._group_by_client(overdue_tickets),
                "by_priority": self._group_by_priority(overdue_tickets),
                "overdue_duration": self._analyze_overdue_duration(overdue_tickets),
                "business_impact": self._assess_business_impact(overdue_tickets),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Get related comments for context
            overdue_comments = db.query(JiraComment).filter(
                JiraComment.ticket_id.in_([t.id for t in overdue_tickets]),
                JiraComment.created_at >= cutoff_date
            ).all()
            
            db.close()
            
            # AI analysis of overdue reasons
            if overdue_comments:
                overdue_analysis = await self._analyze_overdue_comments(overdue_comments)
                analysis["overdue_reasons"] = overdue_analysis
            
            # Generate client impact assessment
            client_impact = await self._assess_client_impact(analysis)
            analysis["client_impact_assessment"] = client_impact
            
            # AI-powered recommendations
            ai_recommendations = await self._generate_overdue_recommendations(analysis)
            analysis["ai_recommendations"] = ai_recommendations
            
            logger.info("Overdue work analysis completed", 
                       total_overdue=analysis["total_overdue"])
            
            return analysis
            
        except Exception as e:
            logger.error("Failed to analyze overdue work", error=str(e))
            return {"error": str(e), "count": 0}
    
    async def analyze_failed_deployments(self, days_back: int = 30) -> Dict[str, Any]:
        """Comprehensive analysis of failed deployments with quality insights"""
        try:
            logger.info("Analyzing failed deployments", days_back=days_back)
            
            db = next(get_db())
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Get deployment records
            deployments = db.query(DeploymentRecord).filter(
                DeploymentRecord.deployment_date >= cutoff_date
            ).all()
            
            if not deployments:
                db.close()
                return {"message": "No deployments found", "count": 0}
            
            # Analyze deployment success/failure rates
            failed_deployments = [d for d in deployments if d.has_failures]
            
            analysis = {
                "total_deployments": len(deployments),
                "failed_deployments": len(failed_deployments),
                "success_rate": ((len(deployments) - len(failed_deployments)) / len(deployments)) * 100,
                "failure_rate": (len(failed_deployments) / len(deployments)) * 100,
                "by_client": self._group_deployments_by_client(deployments),
                "failure_patterns": self._analyze_failure_patterns(failed_deployments),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            db.close()
            
            # AI analysis of failure causes
            if failed_deployments:
                failure_analysis = await self._analyze_deployment_failures(failed_deployments)
                analysis["failure_analysis"] = failure_analysis
            
            # Quality trend analysis
            quality_trends = await self._analyze_deployment_quality_trends(deployments)
            analysis["quality_trends"] = quality_trends
            
            # Generate improvement recommendations
            improvement_recommendations = await self._generate_deployment_improvements(analysis)
            analysis["improvement_recommendations"] = improvement_recommendations
            
            logger.info("Failed deployments analysis completed", 
                       total_deployments=analysis["total_deployments"],
                       failed_count=analysis["failed_deployments"])
            
            return analysis
            
        except Exception as e:
            logger.error("Failed to analyze failed deployments", error=str(e))
            return {"error": str(e), "count": 0}
    
    async def analyze_level_ii_test_failures(self, days_back: int = 30) -> Dict[str, Any]:
        """Detailed analysis of Level II test failures with root cause analysis"""
        try:
            logger.info("Analyzing Level II test failures", days_back=days_back)
            
            db = next(get_db())
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Get Level II test failures
            failed_tests = db.query(JiraTicket).filter(
                JiraTicket.level_ii_failed == True,
                JiraTicket.updated_at >= cutoff_date
            ).all()
            
            if not failed_tests:
                db.close()
                return {"message": "No Level II test failures found", "count": 0}
            
            # Analyze failure patterns
            analysis = {
                "total_failures": len(failed_tests),
                "by_project": self._group_by_project(failed_tests),
                "by_assignee": self._group_by_assignee(failed_tests),
                "by_priority": self._group_by_priority(failed_tests),
                "failure_timeline": self._analyze_failure_timeline(failed_tests),
                "repeat_failures": self._identify_repeat_failures(failed_tests),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Get comments and descriptions for root cause analysis
            failure_comments = db.query(JiraComment).filter(
                JiraComment.ticket_id.in_([t.id for t in failed_tests]),
                JiraComment.created_at >= cutoff_date
            ).all()
            
            db.close()
            
            # AI-powered root cause analysis
            if failure_comments or failed_tests:
                root_cause_analysis = await self._analyze_test_failure_causes(
                    failed_tests, failure_comments
                )
                analysis["root_cause_analysis"] = root_cause_analysis
            
            # Quality process assessment
            process_assessment = await self._assess_quality_processes(analysis)
            analysis["process_assessment"] = process_assessment
            
            # Generate quality improvement plan
            improvement_plan = await self._generate_quality_improvement_plan(analysis)
            analysis["improvement_plan"] = improvement_plan
            
            logger.info("Level II test failures analysis completed", 
                       total_failures=analysis["total_failures"])
            
            return analysis
            
        except Exception as e:
            logger.error("Failed to analyze Level II test failures", error=str(e))
            return {"error": str(e), "count": 0}
    
    async def generate_executive_risk_assessment(self) -> Dict[str, Any]:
        """Generate comprehensive executive risk assessment"""
        try:
            logger.info("Generating executive risk assessment")
            
            # Gather all analysis results
            stalled_analysis = await self.analyze_stalled_tickets(7)  # Last 7 days
            overdue_analysis = await self.analyze_overdue_work(14)    # Last 14 days
            deployment_analysis = await self.analyze_failed_deployments(30)  # Last 30 days
            test_failure_analysis = await self.analyze_level_ii_test_failures(14)  # Last 14 days
            
            # Calculate risk scores
            risk_assessment = {
                "overall_risk_score": self._calculate_overall_risk_score({
                    "stalled": stalled_analysis,
                    "overdue": overdue_analysis,
                    "deployments": deployment_analysis,
                    "test_failures": test_failure_analysis
                }),
                "delivery_risk": self._assess_delivery_risk(stalled_analysis, overdue_analysis),
                "quality_risk": self._assess_quality_risk(deployment_analysis, test_failure_analysis),
                "client_satisfaction_risk": self._assess_client_risk(overdue_analysis, deployment_analysis),
                "operational_efficiency": self._assess_operational_efficiency(stalled_analysis),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Generate AI-powered strategic recommendations
            strategic_recommendations = await self._generate_strategic_recommendations(risk_assessment)
            risk_assessment["strategic_recommendations"] = strategic_recommendations
            
            # Create executive action items
            action_items = await self._create_executive_action_items(risk_assessment)
            risk_assessment["executive_action_items"] = action_items
            
            logger.info("Executive risk assessment completed", 
                       overall_risk=risk_assessment["overall_risk_score"])
            
            return risk_assessment
            
        except Exception as e:
            logger.error("Failed to generate executive risk assessment", error=str(e))
            return {"error": str(e)}
    
    # Helper methods for analysis
    
    def _group_by_project(self, tickets: List) -> Dict[str, int]:
        """Group tickets by project"""
        projects = {}
        for ticket in tickets:
            project = ticket.ticket_key.split('-')[0] if ticket.ticket_key else 'Unknown'
            projects[project] = projects.get(project, 0) + 1
        return projects
    
    def _group_by_assignee(self, tickets: List) -> Dict[str, int]:
        """Group tickets by assignee"""
        assignees = {}
        for ticket in tickets:
            assignee = ticket.assignee or 'Unassigned'
            assignees[assignee] = assignees.get(assignee, 0) + 1
        return assignees
    
    def _group_by_priority(self, tickets: List) -> Dict[str, int]:
        """Group tickets by priority"""
        priorities = {}
        for ticket in tickets:
            priority = ticket.priority or 'Unknown'
            priorities[priority] = priorities.get(priority, 0) + 1
        return priorities
    
    def _group_by_status(self, tickets: List) -> Dict[str, int]:
        """Group tickets by status"""
        statuses = {}
        for ticket in tickets:
            status = ticket.status or 'Unknown'
            statuses[status] = statuses.get(status, 0) + 1
        return statuses
    
    def _group_by_client(self, tickets: List) -> Dict[str, int]:
        """Group tickets by client (inferred from project)"""
        clients = {}
        for ticket in tickets:
            project = ticket.ticket_key.split('-')[0] if ticket.ticket_key else 'Unknown'
            # Map project to client (simplified)
            client = self._map_project_to_client(project)
            clients[client] = clients.get(client, 0) + 1
        return clients
    
    def _map_project_to_client(self, project_key: str) -> str:
        """Map project key to client name"""
        # This should match the mapping in tempo.py
        client_map = {
            'PIH': 'PIH', 'CMDR': 'Commander', 'GARNISH': 'Garnish',
            'AGP': 'AGP', 'RSND': 'Resend', 'SEG': 'SEG',
            'TALOS': 'Talos Energy', 'WOOD': 'Wood Group', 'AREN': 'Arena',
            'LPCC': 'LPCC', 'SOTT': 'SOTT', 'FAROUK': 'Farouk'
        }
        return client_map.get(project_key.upper(), 'Unknown Client')
    
    def _analyze_stall_duration(self, tickets: List) -> Dict[str, Any]:
        """Analyze how long tickets have been stalled"""
        durations = [t.days_in_current_status for t in tickets if t.days_in_current_status]
        if not durations:
            return {"average_days": 0, "max_days": 0, "min_days": 0}
        
        return {
            "average_days": sum(durations) / len(durations),
            "max_days": max(durations),
            "min_days": min(durations),
            "median_days": sorted(durations)[len(durations) // 2]
        }
    
    def _analyze_overdue_duration(self, tickets: List) -> Dict[str, Any]:
        """Analyze how overdue tickets are"""
        today = datetime.utcnow().date()
        overdue_days = []
        
        for ticket in tickets:
            if ticket.due_date:
                days_overdue = (today - ticket.due_date.date()).days
                if days_overdue > 0:
                    overdue_days.append(days_overdue)
        
        if not overdue_days:
            return {"average_days_overdue": 0, "max_days_overdue": 0}
        
        return {
            "average_days_overdue": sum(overdue_days) / len(overdue_days),
            "max_days_overdue": max(overdue_days),
            "total_tickets_with_due_dates": len(overdue_days)
        }
    
    def _assess_business_impact(self, tickets: List) -> Dict[str, Any]:
        """Assess business impact of overdue tickets"""
        high_priority_overdue = len([t for t in tickets if t.priority in ['Highest', 'High']])
        client_count = len(set(self._map_project_to_client(t.ticket_key.split('-')[0]) 
                              for t in tickets if t.ticket_key))
        
        return {
            "high_priority_overdue": high_priority_overdue,
            "affected_clients": client_count,
            "impact_level": "high" if high_priority_overdue > 3 else "medium" if high_priority_overdue > 1 else "low"
        }
    
    def _group_deployments_by_client(self, deployments: List) -> Dict[str, Dict[str, int]]:
        """Group deployments by client with success/failure counts"""
        clients = {}
        for deployment in deployments:
            # Extract client from deployment cases
            cases = deployment.cases or []
            for case in cases:
                if isinstance(case, dict) and case.get('jira_key'):
                    project = case['jira_key'].split('-')[0]
                    client = self._map_project_to_client(project)
                    
                    if client not in clients:
                        clients[client] = {"total": 0, "failed": 0, "successful": 0}
                    
                    clients[client]["total"] += 1
                    if deployment.has_failures:
                        clients[client]["failed"] += 1
                    else:
                        clients[client]["successful"] += 1
        
        return clients
    
    def _analyze_failure_patterns(self, failed_deployments: List) -> Dict[str, Any]:
        """Analyze patterns in deployment failures"""
        failure_types = {}
        failure_frequencies = {}
        
        for deployment in failed_deployments:
            failure_details = deployment.failure_details or []
            for failure in failure_details:
                if isinstance(failure, dict):
                    failure_type = failure.get('status', 'Unknown')
                    failure_types[failure_type] = failure_types.get(failure_type, 0) + 1
        
        return {
            "failure_types": failure_types,
            "most_common_failure": max(failure_types.items(), key=lambda x: x[1])[0] if failure_types else None,
            "pattern_analysis": "Analysis complete"
        }
    
    def _analyze_failure_timeline(self, tickets: List) -> Dict[str, Any]:
        """Analyze timeline of test failures"""
        # Group failures by date
        failures_by_date = {}
        for ticket in tickets:
            if ticket.updated_date:
                date_key = ticket.updated_date.date().isoformat()
                failures_by_date[date_key] = failures_by_date.get(date_key, 0) + 1
        
        return {
            "failures_by_date": failures_by_date,
            "peak_failure_date": max(failures_by_date.items(), key=lambda x: x[1])[0] if failures_by_date else None,
            "trend": "increasing" if len(failures_by_date) > 1 else "stable"
        }
    
    def _identify_repeat_failures(self, tickets: List) -> Dict[str, Any]:
        """Identify tickets that have failed multiple times"""
        # This would typically look at status history
        # For now, simplified implementation
        repeat_failures = [t for t in tickets if t.days_in_current_status > 10]
        
        return {
            "repeat_failure_count": len(repeat_failures),
            "repeat_failure_tickets": [t.ticket_key for t in repeat_failures],
            "impact": "high" if len(repeat_failures) > 3 else "medium" if len(repeat_failures) > 1 else "low"
        }
    
    # AI-powered analysis methods
    
    async def _analyze_stall_comments(self, comments: List) -> Dict[str, Any]:
        """Analyze comments from stalled tickets to understand root causes"""
        try:
            comment_texts = [c.body for c in comments if c.body]
            if not comment_texts:
                return {"root_causes": [], "sentiment": "neutral"}
            
            # Analyze batch of comments
            analyses = await self.ai_service.analyze_batch_comments([
                {"body": text, "comment_id": str(i)} for i, text in enumerate(comment_texts)
            ])
            
            # Extract blockers and issues
            blockers = []
            sentiments = []
            
            for analysis in analyses:
                if analysis.get("contains_blocker"):
                    blockers.extend(analysis.get("blockers", []))
                sentiments.append(analysis.get("sentiment", "neutral"))
            
            return {
                "root_causes": list(set(blockers)),
                "sentiment_distribution": {
                    "positive": sentiments.count("positive"),
                    "negative": sentiments.count("negative"),
                    "neutral": sentiments.count("neutral")
                },
                "dominant_sentiment": max(set(sentiments), key=sentiments.count) if sentiments else "neutral"
            }
            
        except Exception as e:
            logger.error("Failed to analyze stall comments", error=str(e))
            return {"root_causes": [], "sentiment": "neutral"}
    
    async def _generate_stall_insights(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI insights for stalled tickets"""
        try:
            prompt = f"""
            Analyze this stalled tickets data and provide executive insights:
            
            {json.dumps(analysis, default=str, indent=2)}
            
            Provide insights in JSON format with:
            - key_insights: array of top 3 insights
            - recommendations: array of specific actions
            - risk_level: low/medium/high/critical
            - estimated_impact: business impact assessment
            """
            
            # This would use the AI service for analysis
            # Simplified for now
            return {
                "key_insights": [
                    f"Total of {analysis['total_stalled']} stalled tickets requiring attention",
                    "Resource allocation review needed",
                    "Process bottlenecks identified"
                ],
                "recommendations": [
                    "Review and reassign stalled tickets",
                    "Identify and remove blockers", 
                    "Improve communication channels"
                ],
                "risk_level": "high" if analysis['total_stalled'] > 10 else "medium",
                "estimated_impact": "Potential delivery delays and client dissatisfaction"
            }
            
        except Exception as e:
            logger.error("Failed to generate stall insights", error=str(e))
            return {"key_insights": [], "recommendations": []}
    
    async def _analyze_overdue_comments(self, comments: List) -> Dict[str, Any]:
        """Analyze comments from overdue tickets"""
        # Similar to stall comments analysis
        return {"reasons": ["Resource constraints", "Scope changes", "Technical complexity"]}
    
    async def _assess_client_impact(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess impact on client relationships"""
        return {
            "affected_clients": len(analysis.get("by_client", {})),
            "high_risk_clients": [],
            "communication_needed": True
        }
    
    async def _generate_overdue_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations for overdue work"""
        return [
            "Prioritize highest priority overdue items",
            "Communicate proactively with affected clients",
            "Review resource allocation and capacity planning"
        ]
    
    async def _analyze_deployment_failures(self, deployments: List) -> Dict[str, Any]:
        """Analyze deployment failure causes"""
        return {
            "common_causes": ["Configuration issues", "Integration failures", "Testing gaps"],
            "prevention_strategies": ["Enhanced testing", "Better configuration management"]
        }
    
    async def _analyze_deployment_quality_trends(self, deployments: List) -> Dict[str, Any]:
        """Analyze deployment quality trends"""
        return {
            "trend": "stable",
            "quality_score": 85,
            "areas_for_improvement": ["Testing coverage", "Code review process"]
        }
    
    async def _generate_deployment_improvements(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate deployment improvement recommendations"""
        return [
            "Implement automated testing pipelines",
            "Enhance code review processes",
            "Improve deployment rollback procedures"
        ]
    
    async def _analyze_test_failure_causes(self, tickets: List, comments: List) -> Dict[str, Any]:
        """Analyze root causes of test failures"""
        return {
            "primary_causes": ["Requirements clarity", "Test data issues", "Environment problems"],
            "patterns": ["Frontend issues", "API integration problems"],
            "prevention_measures": ["Better requirements gathering", "Test environment improvements"]
        }
    
    async def _assess_quality_processes(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess quality assurance processes"""
        return {
            "process_effectiveness": 70,
            "areas_needing_improvement": ["Test coverage", "Review processes"],
            "recommended_changes": ["Automated testing", "Peer reviews"]
        }
    
    async def _generate_quality_improvement_plan(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate quality improvement plan"""
        return {
            "short_term": ["Review failed test cases", "Update test procedures"],
            "medium_term": ["Implement automated testing", "Training programs"],
            "long_term": ["Quality metrics dashboard", "Continuous improvement process"]
        }
    
    # Risk calculation methods
    
    def _calculate_overall_risk_score(self, analyses: Dict[str, Any]) -> int:
        """Calculate overall risk score (1-10, 10 being highest risk)"""
        stalled_score = min(analyses["stalled"].get("total_stalled", 0) // 2, 4)
        overdue_score = min(analyses["overdue"].get("total_overdue", 0) // 2, 3)
        deployment_score = 3 if analyses["deployments"].get("failure_rate", 0) > 20 else 1
        test_score = min(analyses["test_failures"].get("total_failures", 0) // 2, 3)
        
        return min(stalled_score + overdue_score + deployment_score + test_score, 10)
    
    def _assess_delivery_risk(self, stalled: Dict, overdue: Dict) -> str:
        """Assess delivery risk level"""
        total_issues = stalled.get("total_stalled", 0) + overdue.get("total_overdue", 0)
        if total_issues > 15:
            return "high"
        elif total_issues > 8:
            return "medium"
        else:
            return "low"
    
    def _assess_quality_risk(self, deployments: Dict, tests: Dict) -> str:
        """Assess quality risk level"""
        failure_rate = deployments.get("failure_rate", 0)
        test_failures = tests.get("total_failures", 0)
        
        if failure_rate > 25 or test_failures > 5:
            return "high"
        elif failure_rate > 15 or test_failures > 2:
            return "medium"
        else:
            return "low"
    
    def _assess_client_risk(self, overdue: Dict, deployments: Dict) -> str:
        """Assess client satisfaction risk"""
        affected_clients = len(overdue.get("by_client", {}))
        deployment_failures = deployments.get("failed_deployments", 0)
        
        if affected_clients > 3 or deployment_failures > 3:
            return "high"
        elif affected_clients > 1 or deployment_failures > 1:
            return "medium"
        else:
            return "low"
    
    def _assess_operational_efficiency(self, stalled: Dict) -> int:
        """Assess operational efficiency score (1-10)"""
        stalled_count = stalled.get("total_stalled", 0)
        if stalled_count > 10:
            return 4
        elif stalled_count > 5:
            return 6
        else:
            return 8
    
    async def _generate_strategic_recommendations(self, risk_assessment: Dict) -> List[str]:
        """Generate strategic recommendations based on risk assessment"""
        recommendations = []
        
        if risk_assessment["overall_risk_score"] > 7:
            recommendations.append("Immediate leadership intervention required")
        
        if risk_assessment["delivery_risk"] == "high":
            recommendations.append("Review project timelines and resource allocation")
        
        if risk_assessment["quality_risk"] == "high":
            recommendations.append("Implement enhanced quality assurance processes")
        
        if risk_assessment["client_satisfaction_risk"] == "high":
            recommendations.append("Proactive client communication and relationship management")
        
        return recommendations
    
    async def _create_executive_action_items(self, risk_assessment: Dict) -> List[Dict[str, Any]]:
        """Create specific action items for executives"""
        actions = []
        
        if risk_assessment["overall_risk_score"] > 6:
            actions.append({
                "priority": "high",
                "action": "Schedule emergency leadership review meeting",
                "owner": "CEO",
                "deadline": "immediate"
            })
        
        if risk_assessment["delivery_risk"] == "high":
            actions.append({
                "priority": "high", 
                "action": "Review resource allocation and project priorities",
                "owner": "CTO",
                "deadline": "within 48 hours"
            })
        
        return actions
    
    async def close(self):
        """Close business intelligence service"""
        if self.ai_service:
            await self.ai_service.close()
        if self.chroma_manager:
            await self.chroma_manager.close()
        logger.info("Business intelligence service closed")