"""
AI Analysis Service using GPT-4o-mini for text analysis and summarization
"""
import asyncio
from typing import List, Dict, Any, Optional, Union
from openai import AsyncOpenAI
import json
from datetime import datetime
import tiktoken

from config import settings
from utils.logging import get_logger, log_ai_operation

logger = get_logger(__name__)


class AIAnalysisService:
    """Service for AI-powered text analysis using GPT-4o-mini"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai.api_key)
        self.model = settings.openai.model
        self.max_tokens = settings.openai.max_tokens
        self.temperature = settings.openai.temperature
        self.encoding = tiktoken.encoding_for_model("gpt-4o-mini")
        
    async def analyze_jira_comment(self, comment_text: str, ticket_context: Optional[str] = None) -> Dict[str, Any]:
        """Analyze a JIRA comment for sentiment, blockers, and key insights"""
        try:
            prompt = self._build_comment_analysis_prompt(comment_text, ticket_context)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert project manager analyzing JIRA comments for insights."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            logger.info("JIRA comment analyzed", 
                       sentiment=result.get("sentiment"),
                       has_blocker=result.get("contains_blocker"))
            
            return result
            
        except Exception as e:
            logger.error("Failed to analyze JIRA comment", error=str(e))
            return {
                "sentiment": "neutral",
                "sentiment_score": 0.0,
                "contains_blocker": False,
                "key_issues": [],
                "summary": "Analysis failed",
                "confidence": 0.0
            }
    
    def _build_comment_analysis_prompt(self, comment_text: str, ticket_context: Optional[str] = None) -> str:
        """Build prompt for comment analysis"""
        context_section = ""
        if ticket_context:
            context_section = f"\n\nTicket Context: {ticket_context}"
        
        return f"""
Analyze the following JIRA comment for project management insights:

Comment: {comment_text}{context_section}

Provide analysis in JSON format with these fields:
- sentiment: "positive", "negative", or "neutral"
- sentiment_score: float between -1.0 (very negative) and 1.0 (very positive)
- contains_blocker: boolean indicating if comment mentions blockers or impediments
- key_issues: array of specific issues or concerns mentioned
- blockers: array of specific blockers or impediments identified
- summary: brief summary of the comment's main points
- confidence: float between 0.0 and 1.0 indicating analysis confidence
- action_required: boolean indicating if the comment suggests action is needed
- urgency_level: "low", "medium", "high", or "critical"

Focus on identifying:
- Technical issues or bugs
- Process bottlenecks
- Resource constraints
- Client feedback or concerns
- Testing failures
- Deployment issues
- Team communication problems
"""
    
    async def analyze_case_review(self, case_review_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a case review for executive insights"""
        try:
            prompt = self._build_case_review_prompt(case_review_data)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a senior executive consultant analyzing software development standups for strategic insights."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,  # Larger token limit for comprehensive analysis
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            logger.info("Case review analyzed", 
                       total_cases=case_review_data.get("total_cases"),
                       risk_level=result.get("risk_level"))
            
            return result
            
        except Exception as e:
            logger.error("Failed to analyze case review", error=str(e))
            return {
                "executive_summary": "Analysis failed",
                "key_concerns": [],
                "risk_level": "unknown",
                "recommendations": [],
                "resource_issues": [],
                "client_impact": "unknown"
            }
    
    def _build_case_review_prompt(self, case_review_data: Dict[str, Any]) -> str:
        """Build prompt for case review analysis"""
        # Extract key metrics
        total_cases = case_review_data.get("total_cases", 0)
        critical_count = case_review_data.get("critical_count", 0)
        blocked_count = case_review_data.get("blocked_count", 0)
        stalled_count = case_review_data.get("stalled_count", 0)
        
        # Extract case details
        critical_cases = case_review_data.get("critical_cases", [])
        blocked_cases = case_review_data.get("blocked_cases", [])
        waiting_cases = case_review_data.get("waiting_on_client_cases", [])
        
        # Build case summaries
        case_summaries = []
        
        if critical_cases:
            case_summaries.append("Critical Cases:")
            for case in critical_cases[:5]:  # Limit for token efficiency
                case_summaries.append(f"- {case.get('jira_key', '')}: {case.get('notes', '')}")
        
        if blocked_cases:
            case_summaries.append("\nBlocked Cases:")
            for case in blocked_cases[:5]:
                case_summaries.append(f"- {case.get('jira_key', '')}: {case.get('notes', '')}")
        
        if waiting_cases:
            case_summaries.append("\nWaiting on Client:")
            for case in waiting_cases[:3]:
                case_summaries.append(f"- {case.get('jira_key', '')}: {case.get('notes', '')}")
        
        case_details = "\n".join(case_summaries)
        
        return f"""
Analyze this software development standup for executive-level insights:

METRICS:
- Total Active Cases: {total_cases}
- Critical Cases: {critical_count}
- Blocked Cases: {blocked_count}
- Stalled Cases: {stalled_count}

CASE DETAILS:
{case_details}

Provide analysis in JSON format with these fields:
- executive_summary: 2-3 sentence summary for CEO/executives
- risk_level: "low", "medium", "high", or "critical"
- key_concerns: array of top 3-5 concerns requiring attention
- resource_bottlenecks: array of resource/capacity issues identified
- client_impact: assessment of impact on client deliverables
- process_issues: array of process or workflow problems
- recommendations: array of specific actions for leadership
- trending_problems: patterns or recurring issues
- team_health_score: integer 1-10 (10 being excellent)
- confidence: float 0.0-1.0 indicating analysis confidence

Focus on:
- Strategic implications for business
- Resource allocation issues
- Client relationship risks
- Process improvement opportunities
- Team productivity concerns
- Quality assurance problems
"""
    
    async def analyze_deployment_record(self, deployment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze deployment records for failure patterns and insights"""
        try:
            prompt = self._build_deployment_analysis_prompt(deployment_data)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a DevOps expert analyzing deployment records for quality and process insights."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            logger.info("Deployment record analyzed", 
                       has_failures=deployment_data.get("has_failures"),
                       quality_score=result.get("quality_score"))
            
            return result
            
        except Exception as e:
            logger.error("Failed to analyze deployment record", error=str(e))
            return {
                "deployment_summary": "Analysis failed",
                "quality_score": 0,
                "failure_analysis": [],
                "recommendations": [],
                "risk_assessment": "unknown"
            }
    
    def _build_deployment_analysis_prompt(self, deployment_data: Dict[str, Any]) -> str:
        """Build prompt for deployment analysis"""
        cases = deployment_data.get("cases", [])
        has_failures = deployment_data.get("has_failures", False)
        failure_details = deployment_data.get("failure_details", [])
        
        # Build case summaries
        case_summaries = []
        success_count = 0
        failure_count = 0
        
        for case in cases:
            status = case.get("status", "Unknown")
            jira_key = case.get("jira_key", "")
            notes = case.get("notes", "")
            
            if "failed" in status.lower() or case.get("has_failures", False):
                failure_count += 1
                case_summaries.append(f"FAILED - {jira_key}: {notes}")
            else:
                success_count += 1
                case_summaries.append(f"SUCCESS - {jira_key}: {status}")
        
        case_details = "\n".join(case_summaries[:10])  # Limit for tokens
        
        return f"""
Analyze this deployment record for quality and process insights:

DEPLOYMENT OVERVIEW:
- Total Cases Deployed: {len(cases)}
- Successful Deployments: {success_count}
- Failed Deployments: {failure_count}
- Has Failures: {has_failures}

DEPLOYMENT DETAILS:
{case_details}

FAILURE DETAILS:
{json.dumps(failure_details, indent=2) if failure_details else "No specific failure details"}

Provide analysis in JSON format with these fields:
- deployment_summary: brief summary of deployment outcomes
- quality_score: integer 1-10 (10 being perfect deployment)
- success_rate: percentage of successful deployments
- failure_analysis: array of failure root causes and patterns
- impact_assessment: assessment of business/client impact
- process_improvements: array of suggested process improvements
- risk_factors: array of identified risk factors
- recommendations: array of specific actions to improve quality
- trending_issues: patterns across multiple deployments
- confidence: float 0.0-1.0 indicating analysis confidence

Focus on:
- Root cause analysis of failures
- Process bottlenecks
- Quality assurance gaps
- Team training needs
- Tool or infrastructure issues
"""
    
    async def generate_executive_summary(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive executive summary from analysis data"""
        try:
            prompt = self._build_executive_summary_prompt(analysis_data)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a senior management consultant creating executive summaries for software company CEOs."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,  # Larger limit for comprehensive summary
                temperature=0.1,  # Lower temperature for more consistent summaries
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            logger.info("Executive summary generated", 
                       overall_health=result.get("overall_health_score"))
            
            return result
            
        except Exception as e:
            logger.error("Failed to generate executive summary", error=str(e))
            return {
                "executive_overview": "Summary generation failed",
                "overall_health_score": 5,
                "critical_actions": [],
                "strategic_recommendations": [],
                "risk_assessment": "Unable to assess"
            }
    
    def _build_executive_summary_prompt(self, analysis_data: Dict[str, Any]) -> str:
        """Build prompt for executive summary generation"""
        return f"""
Create an executive summary based on this comprehensive analysis data:

ANALYSIS DATA:
{json.dumps(analysis_data, indent=2, default=str)}

Generate a JSON response with these fields:
- executive_overview: 3-4 sentence summary for the CEO
- overall_health_score: integer 1-10 (10 being excellent organizational health)
- key_metrics: object with important KPIs and trends
- critical_actions: array of top 3 actions requiring immediate CEO attention
- strategic_recommendations: array of longer-term strategic recommendations
- risk_assessment: assessment of current risks to business objectives
- resource_optimization: recommendations for resource allocation
- client_relationship_status: assessment of client satisfaction and risks
- competitive_positioning: how current performance affects market position
- investment_priorities: recommended areas for investment or improvement
- confidence: float 0.0-1.0 indicating summary confidence

Focus on:
- Business impact and strategic implications
- Revenue and client relationship risks
- Operational efficiency opportunities
- Competitive advantages or disadvantages
- Investment and resource allocation guidance
- Leadership intervention requirements
"""
    
    async def analyze_batch_comments(self, comments: List[Dict[str, Any]], 
                                   batch_size: int = 10) -> List[Dict[str, Any]]:
        """Analyze multiple comments in batches to optimize API usage"""
        try:
            results = []
            
            for i in range(0, len(comments), batch_size):
                batch = comments[i:i + batch_size]
                batch_tasks = []
                
                for comment in batch:
                    task = self.analyze_jira_comment(
                        comment.get("body", ""),
                        comment.get("ticket_context", "")
                    )
                    batch_tasks.append(task)
                
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"Failed to analyze comment {i+j}", error=str(result))
                        continue
                    
                    # Add original comment metadata
                    result.update({
                        "comment_id": batch[j].get("comment_id"),
                        "ticket_key": batch[j].get("ticket_key"),
                        "author": batch[j].get("author"),
                        "created_date": batch[j].get("created_date")
                    })
                    results.append(result)
                
                # Small delay to respect rate limits
                await asyncio.sleep(0.1)
            
            logger.info("Batch comment analysis completed", 
                       total_comments=len(comments),
                       successful_analyses=len(results))
            
            return results
            
        except Exception as e:
            logger.error("Batch comment analysis failed", error=str(e))
            return []
    
    async def identify_trends(self, historical_data: List[Dict[str, Any]], 
                            analysis_type: str) -> Dict[str, Any]:
        """Identify trends and patterns from historical analysis data"""
        try:
            prompt = self._build_trend_analysis_prompt(historical_data, analysis_type)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data analyst expert at identifying trends and patterns in software development operations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            logger.info("Trend analysis completed", 
                       analysis_type=analysis_type,
                       data_points=len(historical_data))
            
            return result
            
        except Exception as e:
            logger.error("Failed to identify trends", 
                        analysis_type=analysis_type, error=str(e))
            return {
                "trends": [],
                "patterns": [],
                "predictions": [],
                "recommendations": []
            }
    
    def _build_trend_analysis_prompt(self, historical_data: List[Dict[str, Any]], 
                                   analysis_type: str) -> str:
        """Build prompt for trend analysis"""
        # Limit data for token efficiency
        limited_data = historical_data[-20:] if len(historical_data) > 20 else historical_data
        
        return f"""
Analyze trends and patterns in this {analysis_type} data:

HISTORICAL DATA:
{json.dumps(limited_data, indent=2, default=str)}

Provide analysis in JSON format with these fields:
- trends: array of identified trends (improving, declining, stable)
- patterns: array of recurring patterns or cycles
- predictions: array of predicted future outcomes based on trends
- risk_indicators: array of warning signs or concerning trends
- opportunities: array of positive trends to capitalize on
- recommendations: array of actions based on trend analysis
- confidence: float 0.0-1.0 indicating analysis confidence
- data_quality: assessment of the data quality for trend analysis

Focus on:
- Performance trends over time
- Recurring issues or success patterns
- Seasonal or cyclical patterns
- Leading indicators of problems
- Opportunities for improvement
"""
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text for cost optimization"""
        try:
            return len(self.encoding.encode(text))
        except Exception:
            # Fallback to rough estimation
            return len(text.split()) * 1.3
    
    async def close(self):
        """Close AI service connections"""
        # AsyncOpenAI client doesn't need explicit closing
        logger.info("AI Analysis service closed")