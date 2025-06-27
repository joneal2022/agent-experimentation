"""
JIRA MCP Connector with enhanced data extraction and analysis
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from jira import JIRA
import httpx
from sqlalchemy.orm import Session

from config import settings
from core.database import get_db
from models.jira import JiraProject, JiraTicket, JiraComment, JiraStatusHistory, JiraWorklog
from utils.logging import get_logger, log_data_ingestion

logger = get_logger(__name__)


class JiraMCPConnector:
    """Enhanced JIRA connector with MCP integration"""
    
    def __init__(self):
        self.client = None
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
    async def connect(self) -> bool:
        """Establish connection to JIRA"""
        try:
            self.client = JIRA(
                server=settings.atlassian.jira_url,
                basic_auth=(
                    settings.atlassian.jira_username,
                    settings.atlassian.jira_api_token
                )
            )
            
            # Test connection
            self.client.myself()
            logger.info("JIRA connection established successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to connect to JIRA", error=str(e))
            return False
    
    async def fetch_all_projects(self) -> List[Dict[str, Any]]:
        """Fetch all JIRA projects"""
        try:
            projects = self.client.projects()
            project_data = []
            
            for project in projects:
                project_info = {
                    'key': project.key,
                    'name': project.name,
                    'project_type': getattr(project, 'projectTypeKey', 'unknown'),
                    'lead': getattr(project.lead, 'displayName', None) if hasattr(project, 'lead') else None,
                    'description': getattr(project, 'description', ''),
                    'raw_data': project.raw
                }
                project_data.append(project_info)
            
            logger.info("Fetched JIRA projects", count=len(project_data))
            return project_data
            
        except Exception as e:
            logger.error("Failed to fetch JIRA projects", error=str(e))
            return []
    
    async def fetch_tickets_for_project(self, project_key: str, days_back: int = 30) -> List[Dict[str, Any]]:
        """Fetch all tickets for a specific project"""
        try:
            # Calculate date range for recent updates
            since_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            
            # JQL query to get tickets updated in the last N days
            jql = f'project = {project_key} AND updated >= "{since_date}" ORDER BY updated DESC'
            
            issues = self.client.search_issues(
                jql,
                maxResults=1000,  # Adjust as needed
                expand='changelog,comments,worklog'
            )
            
            ticket_data = []
            for issue in issues:
                ticket_info = await self._extract_ticket_data(issue)
                ticket_data.append(ticket_info)
            
            logger.info("Fetched tickets for project", 
                       project=project_key, 
                       count=len(ticket_data))
            return ticket_data
            
        except Exception as e:
            logger.error("Failed to fetch tickets for project", 
                        project=project_key, error=str(e))
            return []
    
    async def _extract_ticket_data(self, issue) -> Dict[str, Any]:
        """Extract comprehensive data from a JIRA ticket"""
        try:
            # Basic ticket information
            ticket_data = {
                'key': issue.key,
                'summary': issue.fields.summary,
                'description': getattr(issue.fields, 'description', ''),
                'issue_type': issue.fields.issuetype.name,
                'status': issue.fields.status.name,
                'priority': issue.fields.priority.name if issue.fields.priority else 'None',
                'assignee': issue.fields.assignee.displayName if issue.fields.assignee else None,
                'reporter': issue.fields.reporter.displayName if issue.fields.reporter else None,
                'created_date': self._parse_jira_date(issue.fields.created),
                'updated_date': self._parse_jira_date(issue.fields.updated),
                'due_date': self._parse_jira_date(getattr(issue.fields, 'duedate', None)),
                'resolution_date': self._parse_jira_date(issue.fields.resolutiondate),
                'story_points': getattr(issue.fields, 'customfield_10020', None),  # Common story points field
                'raw_data': issue.raw
            }
            
            # Analyze current status duration
            ticket_data['days_in_current_status'] = await self._calculate_days_in_status(issue)
            ticket_data['is_overdue'] = self._check_if_overdue(ticket_data)
            ticket_data['is_stalled'] = ticket_data['days_in_current_status'] > settings.alerts.stalled_ticket_days
            ticket_data['level_ii_failed'] = 'level ii test failed' in ticket_data['status'].lower()
            
            # Extract comments
            ticket_data['comments'] = await self._extract_comments(issue)
            
            # Extract status history
            ticket_data['status_history'] = await self._extract_status_history(issue)
            
            # Extract worklogs
            ticket_data['worklogs'] = await self._extract_worklogs(issue)
            
            return ticket_data
            
        except Exception as e:
            logger.error("Failed to extract ticket data", 
                        ticket_key=issue.key, error=str(e))
            return {}
    
    async def _extract_comments(self, issue) -> List[Dict[str, Any]]:
        """Extract comments from a JIRA ticket"""
        comments = []
        try:
            for comment in issue.fields.comment.comments:
                comment_data = {
                    'comment_id': comment.id,
                    'author': comment.author.displayName,
                    'body': comment.body,
                    'created_date': self._parse_jira_date(comment.created),
                    'updated_date': self._parse_jira_date(comment.updated),
                }
                comments.append(comment_data)
        except Exception as e:
            logger.error("Failed to extract comments", 
                        ticket_key=issue.key, error=str(e))
        
        return comments
    
    async def _extract_status_history(self, issue) -> List[Dict[str, Any]]:
        """Extract status change history from a JIRA ticket"""
        status_history = []
        try:
            for history in issue.changelog.histories:
                for item in history.items:
                    if item.field == 'status':
                        status_change = {
                            'from_status': item.fromString,
                            'to_status': item.toString,
                            'changed_by': history.author.displayName,
                            'changed_at': self._parse_jira_date(history.created),
                        }
                        status_history.append(status_change)
        except Exception as e:
            logger.error("Failed to extract status history", 
                        ticket_key=issue.key, error=str(e))
        
        return status_history
    
    async def _extract_worklogs(self, issue) -> List[Dict[str, Any]]:
        """Extract worklogs from a JIRA ticket"""
        worklogs = []
        try:
            if hasattr(issue.fields, 'worklog') and issue.fields.worklog:
                for worklog in issue.fields.worklog.worklogs:
                    worklog_data = {
                        'worklog_id': worklog.id,
                        'author': worklog.author.displayName,
                        'time_spent_seconds': worklog.timeSpentSeconds,
                        'description': getattr(worklog, 'comment', ''),
                        'started_date': self._parse_jira_date(worklog.started),
                        'created_date': self._parse_jira_date(worklog.created),
                        'updated_date': self._parse_jira_date(worklog.updated),
                    }
                    worklogs.append(worklog_data)
        except Exception as e:
            logger.error("Failed to extract worklogs", 
                        ticket_key=issue.key, error=str(e))
        
        return worklogs
    
    async def _calculate_days_in_status(self, issue) -> int:
        """Calculate how many days the ticket has been in current status"""
        try:
            # Get the most recent status change from changelog
            latest_status_change = None
            for history in reversed(issue.changelog.histories):
                for item in history.items:
                    if item.field == 'status' and item.toString == issue.fields.status.name:
                        latest_status_change = self._parse_jira_date(history.created)
                        break
                if latest_status_change:
                    break
            
            if latest_status_change:
                return (datetime.now() - latest_status_change).days
            else:
                # If no status change found, use created date
                created_date = self._parse_jira_date(issue.fields.created)
                return (datetime.now() - created_date).days
                
        except Exception as e:
            logger.error("Failed to calculate days in status", 
                        ticket_key=issue.key, error=str(e))
            return 0
    
    def _check_if_overdue(self, ticket_data: Dict[str, Any]) -> bool:
        """Check if a ticket is overdue"""
        if ticket_data.get('due_date') and ticket_data.get('resolution_date') is None:
            return datetime.now() > ticket_data['due_date']
        return False
    
    def _parse_jira_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse JIRA date string to datetime object"""
        if not date_str:
            return None
        try:
            # JIRA typically returns dates in ISO format
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception:
            try:
                # Fallback parsing
                return datetime.strptime(date_str[:19], '%Y-%m-%dT%H:%M:%S')
            except Exception as e:
                logger.error("Failed to parse date", date_str=date_str, error=str(e))
                return None
    
    async def get_critical_tickets(self) -> List[Dict[str, Any]]:
        """Get tickets that require immediate attention"""
        try:
            # JQL for critical conditions
            critical_jql = """
            (
                status = "Level II Test Failed" OR
                priority = "Highest" OR
                due < now() OR
                (updated < -5d AND status != "Done" AND status != "Closed")
            ) AND resolution = Unresolved
            ORDER BY priority DESC, updated ASC
            """
            
            issues = self.client.search_issues(critical_jql, maxResults=100)
            critical_tickets = []
            
            for issue in issues:
                ticket_data = await self._extract_ticket_data(issue)
                critical_tickets.append(ticket_data)
            
            logger.info("Found critical tickets", count=len(critical_tickets))
            return critical_tickets
            
        except Exception as e:
            logger.error("Failed to get critical tickets", error=str(e))
            return []
    
    async def close(self):
        """Close the connector and clean up resources"""
        if self.http_client:
            await self.http_client.aclose()
        self.client = None