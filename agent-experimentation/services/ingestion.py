"""
Data ingestion services for JIRA, Confluence, and Tempo
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from core.database import get_db
from connectors.jira import JiraMCPConnector
from connectors.confluence import ConfluenceMCPConnector
from connectors.tempo import TempoMCPConnector
from models.jira import JiraProject, JiraTicket, JiraComment, JiraStatusHistory, JiraWorklog
from models.confluence import ConfluenceSpace, ConfluencePage, CaseReview, DeploymentRecord
from models.tempo import TempoWorklog, TempoTeam, TempoAccount, TempoTimesheet
from utils.logging import get_logger, log_data_ingestion

logger = get_logger(__name__)


class JiraIngestionService:
    """Service for ingesting JIRA data"""
    
    def __init__(self):
        self.connector = JiraMCPConnector()
        
    async def ingest_all_data(self) -> int:
        """Ingest all JIRA data"""
        total_records = 0
        
        try:
            # Connect to JIRA
            if not await self.connector.connect():
                raise Exception("Failed to connect to JIRA")
            
            # Ingest projects
            projects_count = await self.ingest_projects()
            total_records += projects_count
            
            # Ingest tickets for each project
            tickets_count = await self.ingest_tickets()
            total_records += tickets_count
            
            logger.info("JIRA ingestion completed", 
                       total_records=total_records,
                       projects=projects_count,
                       tickets=tickets_count)
            
            return total_records
            
        except Exception as e:
            logger.error("JIRA ingestion failed", error=str(e))
            raise
        finally:
            await self.connector.close()
    
    async def ingest_projects(self) -> int:
        """Ingest JIRA projects"""
        try:
            projects_data = await self.connector.fetch_all_projects()
            
            db = next(get_db())
            records_processed = 0
            
            for project_info in projects_data:
                try:
                    # Check if project already exists
                    existing_project = db.query(JiraProject).filter(
                        JiraProject.project_key == project_info['key']
                    ).first()
                    
                    if existing_project:
                        # Update existing project
                        existing_project.project_name = project_info['name']
                        existing_project.project_type = project_info['project_type']
                        existing_project.lead = project_info['lead']
                        existing_project.description = project_info['description']
                        existing_project.updated_at = datetime.utcnow()
                    else:
                        # Create new project
                        new_project = JiraProject(
                            project_key=project_info['key'],
                            project_name=project_info['name'],
                            project_type=project_info['project_type'],
                            lead=project_info['lead'],
                            description=project_info['description']
                        )
                        db.add(new_project)
                    
                    records_processed += 1
                    
                except Exception as e:
                    logger.error("Failed to process project", 
                               project_key=project_info.get('key'), error=str(e))
            
            db.commit()
            db.close()
            
            logger.info("JIRA projects ingested", count=records_processed)
            return records_processed
            
        except Exception as e:
            logger.error("Failed to ingest JIRA projects", error=str(e))
            return 0
    
    async def ingest_tickets(self) -> int:
        """Ingest JIRA tickets for all projects"""
        try:
            db = next(get_db())
            projects = db.query(JiraProject).all()
            db.close()
            
            total_tickets = 0
            
            for project in projects:
                tickets_data = await self.connector.fetch_tickets_for_project(
                    project.project_key, days_back=30
                )
                
                tickets_count = await self._process_tickets_data(tickets_data, project.id)
                total_tickets += tickets_count
            
            logger.info("JIRA tickets ingested", total_count=total_tickets)
            return total_tickets
            
        except Exception as e:
            logger.error("Failed to ingest JIRA tickets", error=str(e))
            return 0
    
    async def _process_tickets_data(self, tickets_data: List[Dict], project_id: str) -> int:
        """Process and store tickets data"""
        try:
            db = next(get_db())
            records_processed = 0
            
            for ticket_info in tickets_data:
                try:
                    # Check if ticket already exists
                    existing_ticket = db.query(JiraTicket).filter(
                        JiraTicket.ticket_key == ticket_info['key']
                    ).first()
                    
                    if existing_ticket:
                        # Update existing ticket
                        self._update_ticket(existing_ticket, ticket_info)
                    else:
                        # Create new ticket
                        new_ticket = self._create_ticket(ticket_info, project_id)
                        db.add(new_ticket)
                    
                    db.flush()  # Ensure ticket ID is available
                    
                    # Process comments, status history, and worklogs
                    if existing_ticket:
                        ticket_id = existing_ticket.id
                    else:
                        ticket_id = new_ticket.id
                    
                    await self._process_ticket_comments(ticket_info.get('comments', []), ticket_id, db)
                    await self._process_status_history(ticket_info.get('status_history', []), ticket_id, db)
                    await self._process_worklogs(ticket_info.get('worklogs', []), ticket_id, db)
                    
                    records_processed += 1
                    
                except Exception as e:
                    logger.error("Failed to process ticket", 
                               ticket_key=ticket_info.get('key'), error=str(e))
            
            db.commit()
            db.close()
            
            return records_processed
            
        except Exception as e:
            logger.error("Failed to process tickets data", error=str(e))
            return 0
    
    def _create_ticket(self, ticket_info: Dict, project_id: str) -> JiraTicket:
        """Create a new JIRA ticket"""
        return JiraTicket(
            ticket_key=ticket_info['key'],
            project_id=project_id,
            summary=ticket_info['summary'],
            description=ticket_info['description'],
            issue_type=ticket_info['issue_type'],
            status=ticket_info['status'],
            priority=ticket_info['priority'],
            assignee=ticket_info['assignee'],
            reporter=ticket_info['reporter'],
            created_date=ticket_info['created_date'],
            updated_date=ticket_info['updated_date'],
            due_date=ticket_info['due_date'],
            resolution_date=ticket_info['resolution_date'],
            story_points=ticket_info['story_points'],
            days_in_current_status=ticket_info['days_in_current_status'],
            is_overdue=ticket_info['is_overdue'],
            is_stalled=ticket_info['is_stalled'],
            level_ii_failed=ticket_info['level_ii_failed'],
            raw_data=ticket_info['raw_data']
        )
    
    def _update_ticket(self, ticket: JiraTicket, ticket_info: Dict):
        """Update an existing JIRA ticket"""
        ticket.summary = ticket_info['summary']
        ticket.description = ticket_info['description']
        ticket.status = ticket_info['status']
        ticket.priority = ticket_info['priority']
        ticket.assignee = ticket_info['assignee']
        ticket.updated_date = ticket_info['updated_date']
        ticket.due_date = ticket_info['due_date']
        ticket.resolution_date = ticket_info['resolution_date']
        ticket.story_points = ticket_info['story_points']
        ticket.days_in_current_status = ticket_info['days_in_current_status']
        ticket.is_overdue = ticket_info['is_overdue']
        ticket.is_stalled = ticket_info['is_stalled']
        ticket.level_ii_failed = ticket_info['level_ii_failed']
        ticket.raw_data = ticket_info['raw_data']
        ticket.updated_at = datetime.utcnow()
    
    async def _process_ticket_comments(self, comments_data: List[Dict], ticket_id: str, db: Session):
        """Process and store ticket comments"""
        for comment_info in comments_data:
            try:
                existing_comment = db.query(JiraComment).filter(
                    JiraComment.comment_id == comment_info['comment_id']
                ).first()
                
                if not existing_comment:
                    new_comment = JiraComment(
                        ticket_id=ticket_id,
                        comment_id=comment_info['comment_id'],
                        author=comment_info['author'],
                        body=comment_info['body'],
                        created_date=comment_info['created_date'],
                        updated_date=comment_info['updated_date']
                    )
                    db.add(new_comment)
                    
            except Exception as e:
                logger.error("Failed to process comment", 
                           comment_id=comment_info.get('comment_id'), error=str(e))
    
    async def _process_status_history(self, history_data: List[Dict], ticket_id: str, db: Session):
        """Process and store status history"""
        for history_info in history_data:
            try:
                # Check if this status change already exists
                existing_history = db.query(JiraStatusHistory).filter(
                    and_(
                        JiraStatusHistory.ticket_id == ticket_id,
                        JiraStatusHistory.changed_at == history_info['changed_at'],
                        JiraStatusHistory.to_status == history_info['to_status']
                    )
                ).first()
                
                if not existing_history:
                    new_history = JiraStatusHistory(
                        ticket_id=ticket_id,
                        from_status=history_info['from_status'],
                        to_status=history_info['to_status'],
                        changed_by=history_info['changed_by'],
                        changed_at=history_info['changed_at']
                    )
                    db.add(new_history)
                    
            except Exception as e:
                logger.error("Failed to process status history", error=str(e))
    
    async def _process_worklogs(self, worklogs_data: List[Dict], ticket_id: str, db: Session):
        """Process and store worklogs"""
        for worklog_info in worklogs_data:
            try:
                existing_worklog = db.query(JiraWorklog).filter(
                    JiraWorklog.worklog_id == worklog_info['worklog_id']
                ).first()
                
                if not existing_worklog:
                    new_worklog = JiraWorklog(
                        ticket_id=ticket_id,
                        worklog_id=worklog_info['worklog_id'],
                        author=worklog_info['author'],
                        time_spent_seconds=worklog_info['time_spent_seconds'],
                        description=worklog_info['description'],
                        started_date=worklog_info['started_date'],
                        created_date=worklog_info['created_date'],
                        updated_date=worklog_info['updated_date']
                    )
                    db.add(new_worklog)
                    
            except Exception as e:
                logger.error("Failed to process worklog", 
                           worklog_id=worklog_info.get('worklog_id'), error=str(e))


class ConfluenceIngestionService:
    """Service for ingesting Confluence data"""
    
    def __init__(self):
        self.connector = ConfluenceMCPConnector()
        
    async def ingest_all_data(self) -> int:
        """Ingest all Confluence data"""
        total_records = 0
        
        try:
            # Connect to Confluence
            if not await self.connector.connect():
                raise Exception("Failed to connect to Confluence")
            
            # Ingest spaces
            spaces_count = await self.ingest_spaces()
            total_records += spaces_count
            
            # Ingest case reviews
            case_reviews_count = await self.ingest_case_reviews()
            total_records += case_reviews_count
            
            # Ingest deployment records
            deployments_count = await self.ingest_deployment_records()
            total_records += deployments_count
            
            logger.info("Confluence ingestion completed", 
                       total_records=total_records,
                       spaces=spaces_count,
                       case_reviews=case_reviews_count,
                       deployments=deployments_count)
            
            return total_records
            
        except Exception as e:
            logger.error("Confluence ingestion failed", error=str(e))
            raise
        finally:
            await self.connector.close()
    
    async def ingest_spaces(self) -> int:
        """Ingest Confluence spaces"""
        try:
            spaces_data = await self.connector.fetch_all_spaces()
            
            db = next(get_db())
            records_processed = 0
            
            for space_info in spaces_data:
                try:
                    existing_space = db.query(ConfluenceSpace).filter(
                        ConfluenceSpace.space_key == space_info['key']
                    ).first()
                    
                    if existing_space:
                        existing_space.space_name = space_info['name']
                        existing_space.space_type = space_info['type']
                        existing_space.description = space_info['description']
                        existing_space.homepage_id = space_info['homepage_id']
                        existing_space.updated_at = datetime.utcnow()
                    else:
                        new_space = ConfluenceSpace(
                            space_key=space_info['key'],
                            space_name=space_info['name'],
                            space_type=space_info['type'],
                            description=space_info['description'],
                            homepage_id=space_info['homepage_id']
                        )
                        db.add(new_space)
                    
                    records_processed += 1
                    
                except Exception as e:
                    logger.error("Failed to process space", 
                               space_key=space_info.get('key'), error=str(e))
            
            db.commit()
            db.close()
            
            logger.info("Confluence spaces ingested", count=records_processed)
            return records_processed
            
        except Exception as e:
            logger.error("Failed to ingest Confluence spaces", error=str(e))
            return 0
    
    async def ingest_case_reviews(self) -> int:
        """Ingest case review data"""
        try:
            case_reviews_data = await self.connector.extract_case_reviews()
            
            db = next(get_db())
            records_processed = 0
            
            for review_info in case_reviews_data:
                try:
                    existing_review = db.query(CaseReview).filter(
                        CaseReview.page_id == review_info['page_id']
                    ).first()
                    
                    if existing_review:
                        self._update_case_review(existing_review, review_info)
                    else:
                        new_review = self._create_case_review(review_info)
                        db.add(new_review)
                    
                    records_processed += 1
                    
                except Exception as e:
                    logger.error("Failed to process case review", 
                               page_id=review_info.get('page_id'), error=str(e))
            
            db.commit()
            db.close()
            
            logger.info("Case reviews ingested", count=records_processed)
            return records_processed
            
        except Exception as e:
            logger.error("Failed to ingest case reviews", error=str(e))
            return 0
    
    def _create_case_review(self, review_info: Dict) -> CaseReview:
        """Create a new case review"""
        return CaseReview(
            page_id=review_info['page_id'],
            review_date=review_info['review_date'],
            critical_cases=review_info['critical_cases'],
            high_urgency_cases=review_info['high_urgency_cases'],
            blocked_cases=review_info['blocked_cases'],
            waiting_on_client_cases=review_info['waiting_on_client_cases'],
            internal_testing_cases=review_info['internal_testing_cases'],
            client_review_cases=review_info['client_review_cases'],
            prod_ready_cases=review_info['prod_ready_cases'],
            total_cases=review_info['total_cases'],
            critical_count=review_info['critical_count'],
            blocked_count=review_info['blocked_count'],
            overdue_count=review_info['overdue_count'],
            stalled_count=review_info['stalled_count']
        )
    
    def _update_case_review(self, review: CaseReview, review_info: Dict):
        """Update an existing case review"""
        review.review_date = review_info['review_date']
        review.critical_cases = review_info['critical_cases']
        review.high_urgency_cases = review_info['high_urgency_cases']
        review.blocked_cases = review_info['blocked_cases']
        review.waiting_on_client_cases = review_info['waiting_on_client_cases']
        review.internal_testing_cases = review_info['internal_testing_cases']
        review.client_review_cases = review_info['client_review_cases']
        review.prod_ready_cases = review_info['prod_ready_cases']
        review.total_cases = review_info['total_cases']
        review.critical_count = review_info['critical_count']
        review.blocked_count = review_info['blocked_count']
        review.overdue_count = review_info['overdue_count']
        review.stalled_count = review_info['stalled_count']
        review.updated_at = datetime.utcnow()
    
    async def ingest_deployment_records(self) -> int:
        """Ingest deployment records"""
        try:
            deployments_data = await self.connector.extract_deployment_records()
            
            db = next(get_db())
            records_processed = 0
            
            for deployment_info in deployments_data:
                try:
                    # Process each deployment entry
                    for entry in deployment_info.get('entries', []):
                        existing_deployment = db.query(DeploymentRecord).filter(
                            and_(
                                DeploymentRecord.page_id == deployment_info['page_id'],
                                DeploymentRecord.deployment_date == self._parse_deployment_date(entry['date'])
                            )
                        ).first()
                        
                        if existing_deployment:
                            self._update_deployment_record(existing_deployment, entry)
                        else:
                            new_deployment = self._create_deployment_record(deployment_info['page_id'], entry)
                            db.add(new_deployment)
                        
                        records_processed += 1
                        
                except Exception as e:
                    logger.error("Failed to process deployment record", 
                               page_id=deployment_info.get('page_id'), error=str(e))
            
            db.commit()
            db.close()
            
            logger.info("Deployment records ingested", count=records_processed)
            return records_processed
            
        except Exception as e:
            logger.error("Failed to ingest deployment records", error=str(e))
            return 0
    
    def _create_deployment_record(self, page_id: str, entry: Dict) -> DeploymentRecord:
        """Create a new deployment record"""
        # Analyze failures
        has_failures = any(case.get('has_failures', False) for case in entry.get('cases', []))
        failure_details = [case for case in entry.get('cases', []) if case.get('has_failures', False)]
        
        return DeploymentRecord(
            page_id=page_id,
            deployment_date=self._parse_deployment_date(entry['date']),
            cases=entry['cases'],
            has_failures=has_failures,
            failure_details=failure_details,
            deployment_status='DONE'  # Default status
        )
    
    def _update_deployment_record(self, record: DeploymentRecord, entry: Dict):
        """Update an existing deployment record"""
        has_failures = any(case.get('has_failures', False) for case in entry.get('cases', []))
        failure_details = [case for case in entry.get('cases', []) if case.get('has_failures', False)]
        
        record.cases = entry['cases']
        record.has_failures = has_failures
        record.failure_details = failure_details
        record.updated_at = datetime.utcnow()
    
    def _parse_deployment_date(self, date_str: str) -> datetime:
        """Parse deployment date string"""
        try:
            return datetime.strptime(date_str, '%b %d, %Y')
        except:
            try:
                return datetime.strptime(date_str, '%B %d, %Y')
            except:
                return datetime.now()


class TempoIngestionService:
    """Service for ingesting Tempo data"""
    
    def __init__(self):
        self.connector = TempoMCPConnector()
        
    async def ingest_all_data(self) -> int:
        """Ingest all Tempo data"""
        total_records = 0
        
        try:
            # Connect to Tempo
            if not await self.connector.connect():
                raise Exception("Failed to connect to Tempo")
            
            # Ingest teams
            teams_count = await self.ingest_teams()
            total_records += teams_count
            
            # Ingest accounts
            accounts_count = await self.ingest_accounts()
            total_records += accounts_count
            
            # Ingest worklogs
            worklogs_count = await self.ingest_worklogs()
            total_records += worklogs_count
            
            # Ingest timesheets
            timesheets_count = await self.ingest_timesheets()
            total_records += timesheets_count
            
            logger.info("Tempo ingestion completed", 
                       total_records=total_records,
                       teams=teams_count,
                       accounts=accounts_count,
                       worklogs=worklogs_count,
                       timesheets=timesheets_count)
            
            return total_records
            
        except Exception as e:
            logger.error("Tempo ingestion failed", error=str(e))
            raise
        finally:
            await self.connector.close()
    
    async def ingest_teams(self) -> int:
        """Ingest Tempo teams"""
        try:
            teams_data = await self.connector.fetch_teams()
            
            db = next(get_db())
            records_processed = 0
            
            for team_info in teams_data:
                try:
                    existing_team = db.query(TempoTeam).filter(
                        TempoTeam.team_id == team_info['team_id']
                    ).first()
                    
                    if existing_team:
                        existing_team.team_name = team_info['team_name']
                        existing_team.team_lead = team_info['team_lead']
                        existing_team.members = team_info['members']
                        existing_team.permissions = team_info['permissions']
                        existing_team.updated_at = datetime.utcnow()
                    else:
                        new_team = TempoTeam(
                            team_id=team_info['team_id'],
                            team_name=team_info['team_name'],
                            team_lead=team_info['team_lead'],
                            members=team_info['members'],
                            permissions=team_info['permissions']
                        )
                        db.add(new_team)
                    
                    records_processed += 1
                    
                except Exception as e:
                    logger.error("Failed to process team", 
                               team_id=team_info.get('team_id'), error=str(e))
            
            db.commit()
            db.close()
            
            logger.info("Tempo teams ingested", count=records_processed)
            return records_processed
            
        except Exception as e:
            logger.error("Failed to ingest Tempo teams", error=str(e))
            return 0
    
    async def ingest_accounts(self) -> int:
        """Ingest Tempo accounts"""
        try:
            accounts_data = await self.connector.fetch_accounts()
            
            db = next(get_db())
            records_processed = 0
            
            for account_info in accounts_data:
                try:
                    existing_account = db.query(TempoAccount).filter(
                        TempoAccount.account_id == account_info['account_id']
                    ).first()
                    
                    if existing_account:
                        self._update_tempo_account(existing_account, account_info)
                    else:
                        new_account = self._create_tempo_account(account_info)
                        db.add(new_account)
                    
                    records_processed += 1
                    
                except Exception as e:
                    logger.error("Failed to process account", 
                               account_id=account_info.get('account_id'), error=str(e))
            
            db.commit()
            db.close()
            
            logger.info("Tempo accounts ingested", count=records_processed)
            return records_processed
            
        except Exception as e:
            logger.error("Failed to ingest Tempo accounts", error=str(e))
            return 0
    
    def _create_tempo_account(self, account_info: Dict) -> TempoAccount:
        """Create a new Tempo account"""
        return TempoAccount(
            account_id=account_info['account_id'],
            account_key=account_info['account_key'],
            account_name=account_info['account_name'],
            status=account_info['status'],
            customer=account_info['customer'],
            lead=account_info['lead'],
            default_hourly_rate=account_info['default_hourly_rate'],
            billing_type=account_info['billing_type'],
            jira_project_keys=account_info['jira_project_keys'],
            raw_data=account_info['raw_data']
        )
    
    def _update_tempo_account(self, account: TempoAccount, account_info: Dict):
        """Update an existing Tempo account"""
        account.account_name = account_info['account_name']
        account.status = account_info['status']
        account.customer = account_info['customer']
        account.lead = account_info['lead']
        account.default_hourly_rate = account_info['default_hourly_rate']
        account.billing_type = account_info['billing_type']
        account.jira_project_keys = account_info['jira_project_keys']
        account.raw_data = account_info['raw_data']
        account.updated_at = datetime.utcnow()
    
    async def ingest_worklogs(self) -> int:
        """Ingest Tempo worklogs"""
        try:
            worklogs_data = await self.connector.fetch_worklogs(days_back=30)
            
            db = next(get_db())
            records_processed = 0
            
            for worklog_info in worklogs_data:
                try:
                    existing_worklog = db.query(TempoWorklog).filter(
                        TempoWorklog.tempo_worklog_id == worklog_info['tempo_worklog_id']
                    ).first()
                    
                    if not existing_worklog:
                        new_worklog = TempoWorklog(
                            tempo_worklog_id=worklog_info['tempo_worklog_id'],
                            jira_ticket_key=worklog_info['jira_ticket_key'],
                            jira_ticket_id=worklog_info['jira_ticket_id'],
                            time_spent_seconds=worklog_info['time_spent_seconds'],
                            time_spent_hours=worklog_info['time_spent_hours'],
                            billing_key=worklog_info['billing_key'],
                            author_account_id=worklog_info['author_account_id'],
                            author_display_name=worklog_info['author_display_name'],
                            start_date=worklog_info['start_date'],
                            start_time=worklog_info['start_time'],
                            description=worklog_info['description'],
                            attributes=worklog_info['attributes'],
                            raw_data=worklog_info['raw_data']
                        )
                        db.add(new_worklog)
                        records_processed += 1
                    
                except Exception as e:
                    logger.error("Failed to process worklog", 
                               worklog_id=worklog_info.get('tempo_worklog_id'), error=str(e))
            
            db.commit()
            db.close()
            
            logger.info("Tempo worklogs ingested", count=records_processed)
            return records_processed
            
        except Exception as e:
            logger.error("Failed to ingest Tempo worklogs", error=str(e))
            return 0
    
    async def ingest_timesheets(self) -> int:
        """Ingest Tempo timesheets"""
        try:
            timesheets_data = await self.connector.fetch_timesheets(days_back=30)
            
            db = next(get_db())
            records_processed = 0
            
            for timesheet_info in timesheets_data:
                try:
                    existing_timesheet = db.query(TempoTimesheet).filter(
                        and_(
                            TempoTimesheet.user_account_id == timesheet_info['user_account_id'],
                            TempoTimesheet.period_start == timesheet_info['period_start'],
                            TempoTimesheet.period_end == timesheet_info['period_end']
                        )
                    ).first()
                    
                    if existing_timesheet:
                        self._update_timesheet(existing_timesheet, timesheet_info)
                    else:
                        new_timesheet = self._create_timesheet(timesheet_info)
                        db.add(new_timesheet)
                    
                    records_processed += 1
                    
                except Exception as e:
                    logger.error("Failed to process timesheet", error=str(e))
            
            db.commit()
            db.close()
            
            logger.info("Tempo timesheets ingested", count=records_processed)
            return records_processed
            
        except Exception as e:
            logger.error("Failed to ingest Tempo timesheets", error=str(e))
            return 0
    
    def _create_timesheet(self, timesheet_info: Dict) -> TempoTimesheet:
        """Create a new timesheet"""
        return TempoTimesheet(
            user_account_id=timesheet_info['user_account_id'],
            user_display_name=timesheet_info['user_display_name'],
            period_start=timesheet_info['period_start'],
            period_end=timesheet_info['period_end'],
            total_hours=timesheet_info['total_hours'],
            billable_hours=timesheet_info['billable_hours'],
            non_billable_hours=timesheet_info['non_billable_hours'],
            project_breakdown=timesheet_info['project_breakdown'],
            client_breakdown=timesheet_info['client_breakdown'],
            submitted=timesheet_info['submitted'],
            approval_status=timesheet_info['approval_status']
        )
    
    def _update_timesheet(self, timesheet: TempoTimesheet, timesheet_info: Dict):
        """Update an existing timesheet"""
        timesheet.total_hours = timesheet_info['total_hours']
        timesheet.billable_hours = timesheet_info['billable_hours']
        timesheet.non_billable_hours = timesheet_info['non_billable_hours']
        timesheet.project_breakdown = timesheet_info['project_breakdown']
        timesheet.client_breakdown = timesheet_info['client_breakdown']
        timesheet.submitted = timesheet_info['submitted']
        timesheet.approval_status = timesheet_info['approval_status']
        timesheet.updated_at = datetime.utcnow()