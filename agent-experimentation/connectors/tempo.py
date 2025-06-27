"""
Tempo MCP Connector for time tracking data
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import httpx

from config import settings
from utils.logging import get_logger, log_data_ingestion

logger = get_logger(__name__)


class TempoMCPConnector:
    """Enhanced Tempo connector with MCP integration"""
    
    def __init__(self):
        self.base_url = "https://api.tempo.io/core/3"
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {settings.atlassian.tempo_api_token}",
                "Content-Type": "application/json"
            }
        )
        
    async def connect(self) -> bool:
        """Test connection to Tempo API"""
        try:
            response = await self.http_client.get(f"{self.base_url}/worklogs", 
                                                params={"limit": 1})
            response.raise_for_status()
            
            logger.info("Tempo connection established successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to connect to Tempo", error=str(e))
            return False
    
    async def fetch_worklogs(self, days_back: int = 30) -> List[Dict[str, Any]]:
        """Fetch worklogs from the last N days"""
        try:
            # Calculate date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days_back)
            
            all_worklogs = []
            offset = 0
            limit = 1000
            
            while True:
                params = {
                    "from": start_date.isoformat(),
                    "to": end_date.isoformat(),
                    "offset": offset,
                    "limit": limit
                }
                
                response = await self.http_client.get(f"{self.base_url}/worklogs", 
                                                    params=params)
                response.raise_for_status()
                
                data = response.json()
                worklogs = data.get("results", [])
                
                if not worklogs:
                    break
                
                # Process each worklog
                for worklog in worklogs:
                    worklog_data = await self._extract_worklog_data(worklog)
                    all_worklogs.append(worklog_data)
                
                # Check if we have more data
                if len(worklogs) < limit:
                    break
                
                offset += limit
            
            logger.info("Fetched Tempo worklogs", count=len(all_worklogs))
            return all_worklogs
            
        except Exception as e:
            logger.error("Failed to fetch Tempo worklogs", error=str(e))
            return []
    
    async def _extract_worklog_data(self, worklog: Dict[str, Any]) -> Dict[str, Any]:
        """Extract comprehensive data from a Tempo worklog"""
        try:
            worklog_data = {
                'tempo_worklog_id': worklog.get('tempoWorklogId'),
                'jira_ticket_key': worklog.get('issue', {}).get('key'),
                'jira_ticket_id': worklog.get('issue', {}).get('id'),
                'time_spent_seconds': worklog.get('timeSpentSeconds', 0),
                'time_spent_hours': round(worklog.get('timeSpentSeconds', 0) / 3600, 2),
                'billing_key': worklog.get('billableSeconds', {}).get('key') if worklog.get('billableSeconds') else None,
                'author_account_id': worklog.get('author', {}).get('accountId'),
                'author_display_name': worklog.get('author', {}).get('displayName'),
                'start_date': self._parse_tempo_date(worklog.get('startDate')),
                'start_time': worklog.get('startTime'),
                'description': worklog.get('description', ''),
                'attributes': worklog.get('attributes', {}),
                'raw_data': worklog
            }
            
            return worklog_data
            
        except Exception as e:
            logger.error("Failed to extract worklog data", 
                        worklog_id=worklog.get('tempoWorklogId'), error=str(e))
            return {}
    
    async def fetch_teams(self) -> List[Dict[str, Any]]:
        """Fetch all Tempo teams"""
        try:
            response = await self.http_client.get(f"{self.base_url}/teams")
            response.raise_for_status()
            
            data = response.json()
            teams = data.get("results", [])
            
            team_data = []
            for team in teams:
                team_info = {
                    'team_id': team.get('id'),
                    'team_name': team.get('name'),
                    'team_lead': team.get('lead', {}).get('displayName') if team.get('lead') else None,
                    'members': await self._fetch_team_members(team.get('id')),
                    'permissions': team.get('permissions', {}),
                    'raw_data': team
                }
                team_data.append(team_info)
            
            logger.info("Fetched Tempo teams", count=len(team_data))
            return team_data
            
        except Exception as e:
            logger.error("Failed to fetch Tempo teams", error=str(e))
            return []
    
    async def _fetch_team_members(self, team_id: int) -> List[Dict[str, Any]]:
        """Fetch members for a specific team"""
        try:
            response = await self.http_client.get(f"{self.base_url}/teams/{team_id}/members")
            response.raise_for_status()
            
            data = response.json()
            members = data.get("results", [])
            
            member_data = []
            for member in members:
                member_info = {
                    'account_id': member.get('member', {}).get('accountId'),
                    'display_name': member.get('member', {}).get('displayName'),
                    'email': member.get('member', {}).get('emailAddress'),
                    'active': member.get('active', True),
                    'role': member.get('role'),
                    'membership_from': self._parse_tempo_date(member.get('from')),
                    'membership_to': self._parse_tempo_date(member.get('to'))
                }
                member_data.append(member_info)
            
            return member_data
            
        except Exception as e:
            logger.error("Failed to fetch team members", team_id=team_id, error=str(e))
            return []
    
    async def fetch_accounts(self) -> List[Dict[str, Any]]:
        """Fetch all Tempo accounts for billing"""
        try:
            response = await self.http_client.get(f"{self.base_url}/accounts")
            response.raise_for_status()
            
            data = response.json()
            accounts = data.get("results", [])
            
            account_data = []
            for account in accounts:
                account_info = {
                    'account_id': account.get('id'),
                    'account_key': account.get('key'),
                    'account_name': account.get('name'),
                    'status': account.get('status'),
                    'customer': account.get('customer', {}).get('displayName') if account.get('customer') else None,
                    'lead': account.get('lead', {}).get('displayName') if account.get('lead') else None,
                    'default_hourly_rate': account.get('defaultHourlyRate'),
                    'billing_type': 'BILLABLE' if account.get('billable') else 'NON_BILLABLE',
                    'jira_project_keys': [link.get('projectKey') for link in account.get('links', [])],
                    'raw_data': account
                }
                account_data.append(account_info)
            
            logger.info("Fetched Tempo accounts", count=len(account_data))
            return account_data
            
        except Exception as e:
            logger.error("Failed to fetch Tempo accounts", error=str(e))
            return []
    
    async def fetch_timesheets(self, days_back: int = 30) -> List[Dict[str, Any]]:
        """Fetch timesheets for the last N days"""
        try:
            # Calculate date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days_back)
            
            # Get all users first
            users = await self._fetch_all_users()
            
            timesheet_data = []
            
            for user in users:
                user_timesheets = await self._fetch_user_timesheets(
                    user['account_id'], start_date, end_date
                )
                timesheet_data.extend(user_timesheets)
            
            logger.info("Fetched Tempo timesheets", count=len(timesheet_data))
            return timesheet_data
            
        except Exception as e:
            logger.error("Failed to fetch Tempo timesheets", error=str(e))
            return []
    
    async def _fetch_all_users(self) -> List[Dict[str, Any]]:
        """Fetch all users from teams"""
        try:
            teams = await self.fetch_teams()
            users = []
            user_ids = set()
            
            for team in teams:
                for member in team.get('members', []):
                    account_id = member.get('account_id')
                    if account_id and account_id not in user_ids:
                        users.append({
                            'account_id': account_id,
                            'display_name': member.get('display_name'),
                            'email': member.get('email')
                        })
                        user_ids.add(account_id)
            
            return users
            
        except Exception as e:
            logger.error("Failed to fetch all users", error=str(e))
            return []
    
    async def _fetch_user_timesheets(self, user_account_id: str, start_date, end_date) -> List[Dict[str, Any]]:
        """Fetch timesheets for a specific user"""
        try:
            # Calculate weekly periods
            timesheets = []
            current_date = start_date
            
            while current_date <= end_date:
                # Get week boundaries (Monday to Sunday)
                week_start = current_date - timedelta(days=current_date.weekday())
                week_end = week_start + timedelta(days=6)
                
                # Fetch worklogs for this week
                params = {
                    "from": week_start.isoformat(),
                    "to": min(week_end, end_date).isoformat(),
                    "author": user_account_id
                }
                
                response = await self.http_client.get(f"{self.base_url}/worklogs", 
                                                    params=params)
                response.raise_for_status()
                
                data = response.json()
                week_worklogs = data.get("results", [])
                
                if week_worklogs:
                    timesheet = await self._create_timesheet_summary(
                        user_account_id, week_start, week_end, week_worklogs
                    )
                    timesheets.append(timesheet)
                
                current_date = week_end + timedelta(days=1)
            
            return timesheets
            
        except Exception as e:
            logger.error("Failed to fetch user timesheets", 
                        user_id=user_account_id, error=str(e))
            return []
    
    async def _create_timesheet_summary(self, user_account_id: str, week_start, week_end, 
                                      worklogs: List[Dict]) -> Dict[str, Any]:
        """Create a timesheet summary from worklogs"""
        try:
            total_seconds = sum(worklog.get('timeSpentSeconds', 0) for worklog in worklogs)
            total_hours = round(total_seconds / 3600, 2)
            
            # Calculate billable vs non-billable hours
            billable_seconds = sum(
                worklog.get('timeSpentSeconds', 0) 
                for worklog in worklogs 
                if worklog.get('billableSeconds')
            )
            billable_hours = round(billable_seconds / 3600, 2)
            non_billable_hours = total_hours - billable_hours
            
            # Project breakdown
            project_breakdown = {}
            client_breakdown = {}
            
            for worklog in worklogs:
                project_key = worklog.get('issue', {}).get('key', '').split('-')[0]
                time_hours = round(worklog.get('timeSpentSeconds', 0) / 3600, 2)
                
                if project_key:
                    project_breakdown[project_key] = project_breakdown.get(project_key, 0) + time_hours
                    
                    # Map project to client (simplified)
                    client = self._map_project_to_client(project_key)
                    if client:
                        client_breakdown[client] = client_breakdown.get(client, 0) + time_hours
            
            # Get user info
            user_info = next(
                (wl.get('author', {}) for wl in worklogs if wl.get('author')),
                {}
            )
            
            timesheet = {
                'user_account_id': user_account_id,
                'user_display_name': user_info.get('displayName', ''),
                'period_start': week_start,
                'period_end': week_end,
                'total_hours': total_hours,
                'billable_hours': billable_hours,
                'non_billable_hours': non_billable_hours,
                'project_breakdown': project_breakdown,
                'client_breakdown': client_breakdown,
                'submitted': 'DRAFT',  # Default status
                'approval_status': 'PENDING'
            }
            
            return timesheet
            
        except Exception as e:
            logger.error("Failed to create timesheet summary", error=str(e))
            return {}
    
    def _map_project_to_client(self, project_key: str) -> Optional[str]:
        """Map project key to client name (simplified mapping)"""
        # This is a simplified mapping - in real implementation,
        # you would have a more sophisticated mapping system
        project_client_map = {
            'PIH': 'PIH',
            'CMDR': 'Commander',
            'GARNISH': 'Garnish',
            'AGP': 'AGP',
            'RSND': 'Resend',
            'SEG': 'SEG',
            'TALOS': 'Talos Energy',
            'WOOD': 'Wood Group',
            'AREN': 'Arena',
            'LPCC': 'LPCC',
            'SOTT': 'SOTT',
            'FAROUK': 'Farouk',
            'AS': 'AS',
            'ROUSES': 'Rouses',
            'PROARTS': 'ProArts',
            'HAL': 'HAL',
            'WFO': 'WFO',
            'WFA': 'WFA',
            'REDS': 'REDS'
        }
        
        return project_client_map.get(project_key.upper())
    
    async def get_productivity_metrics(self, days_back: int = 30) -> Dict[str, Any]:
        """Get productivity metrics for the specified period"""
        try:
            # Fetch data
            worklogs = await self.fetch_worklogs(days_back)
            teams = await self.fetch_teams()
            accounts = await self.fetch_accounts()
            
            # Calculate metrics
            metrics = {
                'total_hours_logged': sum(wl.get('time_spent_hours', 0) for wl in worklogs),
                'total_worklogs': len(worklogs),
                'unique_contributors': len(set(wl.get('author_account_id') for wl in worklogs if wl.get('author_account_id'))),
                'project_distribution': {},
                'client_distribution': {},
                'team_utilization': {},
                'top_contributors': {}
            }
            
            # Project distribution
            for worklog in worklogs:
                project_key = worklog.get('jira_ticket_key', '').split('-')[0] if worklog.get('jira_ticket_key') else 'Unknown'
                hours = worklog.get('time_spent_hours', 0)
                metrics['project_distribution'][project_key] = metrics['project_distribution'].get(project_key, 0) + hours
            
            # Client distribution
            for project, hours in metrics['project_distribution'].items():
                client = self._map_project_to_client(project)
                if client:
                    metrics['client_distribution'][client] = metrics['client_distribution'].get(client, 0) + hours
            
            # Top contributors
            contributor_hours = {}
            for worklog in worklogs:
                author = worklog.get('author_display_name', 'Unknown')
                hours = worklog.get('time_spent_hours', 0)
                contributor_hours[author] = contributor_hours.get(author, 0) + hours
            
            metrics['top_contributors'] = dict(
                sorted(contributor_hours.items(), key=lambda x: x[1], reverse=True)[:10]
            )
            
            logger.info("Calculated productivity metrics", 
                       total_hours=metrics['total_hours_logged'],
                       contributors=metrics['unique_contributors'])
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to get productivity metrics", error=str(e))
            return {}
    
    def _parse_tempo_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse Tempo date string to datetime object"""
        if not date_str:
            return None
        try:
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                return datetime.strptime(date_str, '%Y-%m-%d')
        except Exception as e:
            logger.error("Failed to parse Tempo date", date_str=date_str, error=str(e))
            return None
    
    async def close(self):
        """Close the connector and clean up resources"""
        if self.http_client:
            await self.http_client.aclose()