"""
Confluence MCP Connector with enhanced content extraction and analysis
"""
import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from atlassian import Confluence
import httpx
from bs4 import BeautifulSoup

from config import settings
from utils.logging import get_logger, log_data_ingestion

logger = get_logger(__name__)


class ConfluenceMCPConnector:
    """Enhanced Confluence connector with MCP integration"""
    
    def __init__(self):
        self.client = None
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
    async def connect(self) -> bool:
        """Establish connection to Confluence"""
        try:
            self.client = Confluence(
                url=settings.atlassian.confluence_url,
                username=settings.atlassian.confluence_username,
                password=settings.atlassian.confluence_api_token,
                cloud=True
            )
            
            # Test connection
            self.client.get_all_spaces(limit=1)
            logger.info("Confluence connection established successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to connect to Confluence", error=str(e))
            return False
    
    async def fetch_all_spaces(self) -> List[Dict[str, Any]]:
        """Fetch all Confluence spaces"""
        try:
            spaces = self.client.get_all_spaces()
            space_data = []
            
            for space in spaces['results']:
                space_info = {
                    'key': space['key'],
                    'name': space['name'],
                    'type': space['type'],
                    'description': space.get('description', {}).get('plain', {}).get('value', ''),
                    'homepage_id': space.get('homepage', {}).get('id'),
                    'raw_data': space
                }
                space_data.append(space_info)
            
            logger.info("Fetched Confluence spaces", count=len(space_data))
            return space_data
            
        except Exception as e:
            logger.error("Failed to fetch Confluence spaces", error=str(e))
            return []
    
    async def fetch_pages_in_space(self, space_key: str, days_back: int = 30) -> List[Dict[str, Any]]:
        """Fetch all pages in a specific space"""
        try:
            # Get pages updated in the last N days
            pages = self.client.get_all_pages_from_space(
                space_key,
                expand='body.storage,version,history,ancestors'
            )
            
            page_data = []
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            for page in pages:
                page_info = await self._extract_page_data(page, space_key)
                
                # Filter by date if specified
                if page_info.get('updated_date'):
                    # Ensure both dates are timezone-naive for comparison
                    updated_date = page_info['updated_date']
                    if updated_date.tzinfo is not None:
                        updated_date = updated_date.replace(tzinfo=None)
                    
                    cutoff_naive = cutoff_date.replace(tzinfo=None) if cutoff_date.tzinfo else cutoff_date
                    
                    if updated_date > cutoff_naive:
                        page_data.append(page_info)
                elif days_back is None:  # Include all pages if no date filter
                    page_data.append(page_info)
            
            logger.info("Fetched pages from space", 
                       space=space_key, 
                       count=len(page_data))
            return page_data
            
        except Exception as e:
            logger.error("Failed to fetch pages from space", 
                        space=space_key, error=str(e))
            return []
    
    async def _extract_page_data(self, page: Dict[str, Any], space_key: str) -> Dict[str, Any]:
        """Extract comprehensive data from a Confluence page"""
        try:
            page_data = {
                'page_id': page['id'],
                'space_key': space_key,
                'title': page['title'],
                'content_type': page['type'],
                'version': page['version']['number'],
                'created_date': self._parse_confluence_date(page['history']['createdDate']),
                'updated_date': self._parse_confluence_date(page['version']['when']),
                'author': page['version']['by']['displayName'],
                'parent_id': page.get('ancestors', [{}])[-1].get('id') if page.get('ancestors') else None,
                'raw_data': page
            }
            
            # Extract and clean content
            if 'body' in page and 'storage' in page['body']:
                raw_content = page['body']['storage']['value']
                page_data['content'] = self._clean_html_content(raw_content)
            else:
                page_data['content'] = ''
            
            return page_data
            
        except Exception as e:
            logger.error("Failed to extract page data", 
                        page_id=page.get('id'), error=str(e))
            return {}
    
    def _clean_html_content(self, html_content: str) -> str:
        """Clean and extract text from HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text and clean up whitespace
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            logger.error("Failed to clean HTML content", error=str(e))
            return html_content
    
    async def extract_case_reviews(self, space_key: str = None) -> List[Dict[str, Any]]:
        """Extract case review (standup) information from Confluence"""
        try:
            # Search for case review pages
            search_query = 'title:"Case Review" OR title:"Daily Standup" OR title:"Standup"'
            if space_key:
                search_query += f' AND space:{space_key}'
            
            search_results = self.client.cql(search_query, limit=50)
            case_reviews = []
            
            for result in search_results['results']:
                page_content = self.client.get_page_by_id(
                    result['id'], 
                    expand='body.storage,version'
                )
                
                case_review_data = await self._parse_case_review_content(page_content)
                if case_review_data:
                    case_reviews.append(case_review_data)
            
            logger.info("Extracted case reviews", count=len(case_reviews))
            return case_reviews
            
        except Exception as e:
            logger.error("Failed to extract case reviews", error=str(e))
            return []
    
    async def _parse_case_review_content(self, page: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse case review content to extract structured data"""
        try:
            content = page['body']['storage']['value']
            clean_text = self._clean_html_content(content)
            
            # Extract review date from title or content
            review_date = self._extract_review_date(page['title'], clean_text)
            if not review_date:
                review_date = self._parse_confluence_date(page['version']['when'])
            
            case_review = {
                'page_id': page['id'],
                'review_date': review_date,
                'title': page['title'],
                'content': clean_text,
                'critical_cases': self._extract_section_data(clean_text, 'Critical Cases'),
                'high_urgency_cases': self._extract_section_data(clean_text, 'High Urgency Cases'),
                'blocked_cases': self._extract_section_data(clean_text, 'Blocked Cases'),
                'waiting_on_client_cases': self._extract_section_data(clean_text, 'Waiting on Client Cases'),
                'internal_testing_cases': self._extract_section_data(clean_text, 'Cases In Internal Testing'),
                'client_review_cases': self._extract_section_data(clean_text, 'Cases Ready for Review'),
                'prod_ready_cases': self._extract_section_data(clean_text, 'Ready for Prod Cases'),
                'raw_data': page
            }
            
            # Calculate summary statistics
            case_review.update(self._calculate_case_review_stats(case_review))
            
            return case_review
            
        except Exception as e:
            logger.error("Failed to parse case review content", 
                        page_id=page.get('id'), error=str(e))
            return None
    
    def _extract_section_data(self, content: str, section_name: str) -> List[Dict[str, Any]]:
        """Extract cases from a specific section of the case review"""
        try:
            # Find the section in the content
            section_pattern = rf'{section_name}:?\s*\n(.*?)(?=\n\n[A-Z]|\Z)'
            section_match = re.search(section_pattern, content, re.DOTALL | re.IGNORECASE)
            
            if not section_match:
                return []
            
            section_content = section_match.group(1)
            cases = []
            
            # Parse individual cases (assumes format: JIRA-123: Description)
            case_pattern = r'([A-Z]+-\d+):?\s*(.*?)(?=\n[A-Z]+-\d+|\n\n|\Z)'
            case_matches = re.findall(case_pattern, section_content, re.DOTALL)
            
            for jira_key, description in case_matches:
                # Further parse the description for priority and notes
                priority_match = re.search(r'(Highest|High|Medium|Low|Hotfix)', description, re.IGNORECASE)
                priority = priority_match.group(1) if priority_match else 'Unknown'
                
                # Extract notes (everything after priority)
                notes = re.sub(r'^.*?(Highest|High|Medium|Low|Hotfix)\s*', '', description, flags=re.IGNORECASE).strip()
                
                case_data = {
                    'jira_key': jira_key.strip(),
                    'priority': priority,
                    'notes': notes,
                    'section': section_name,
                    'raw_text': description.strip()
                }
                cases.append(case_data)
            
            return cases
            
        except Exception as e:
            logger.error("Failed to extract section data", 
                        section=section_name, error=str(e))
            return []
    
    def _calculate_case_review_stats(self, case_review: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate summary statistics for a case review"""
        try:
            total_cases = 0
            critical_count = len(case_review.get('critical_cases', []))
            blocked_count = len(case_review.get('blocked_cases', []))
            
            # Count all cases
            for section_key in ['critical_cases', 'high_urgency_cases', 'blocked_cases', 
                              'waiting_on_client_cases', 'internal_testing_cases', 
                              'client_review_cases', 'prod_ready_cases']:
                total_cases += len(case_review.get(section_key, []))
            
            # Count overdue cases (would need JIRA integration to determine actual due dates)
            overdue_count = 0
            stalled_count = blocked_count  # Blocked cases are essentially stalled
            
            return {
                'total_cases': total_cases,
                'critical_count': critical_count,
                'blocked_count': blocked_count,
                'overdue_count': overdue_count,
                'stalled_count': stalled_count
            }
            
        except Exception as e:
            logger.error("Failed to calculate case review stats", error=str(e))
            return {
                'total_cases': 0,
                'critical_count': 0,
                'blocked_count': 0,
                'overdue_count': 0,
                'stalled_count': 0
            }
    
    async def extract_deployment_records(self, space_key: str = None) -> List[Dict[str, Any]]:
        """Extract deployment information from Confluence"""
        try:
            # Search for deployment pages with proper CQL syntax
            search_query = 'title ~ "Deployment" OR title ~ "Deploy" OR text ~ "DONE" OR text ~ "DEPLOYED TO PROD"'
            if space_key:
                search_query += f' AND space = "{space_key}"'
            
            search_results = self.client.cql(search_query, limit=100)
            deployments = []
            
            for result in search_results['results']:
                try:
                    # Handle different result structures
                    page_id = result.get('content', {}).get('id') or result.get('id')
                    if not page_id:
                        logger.warning("No page ID found in result", result_keys=list(result.keys()))
                        continue
                    
                    page_content = self.client.get_page_by_id(
                        page_id, 
                        expand='body.storage,version'
                    )
                    
                    deployment_data = await self._parse_deployment_content(page_content)
                    if deployment_data:
                        deployments.append(deployment_data)
                except Exception as e:
                    logger.warning("Failed to process deployment search result", error=str(e))
                    continue
            
            logger.info("Extracted deployment records", count=len(deployments))
            return deployments
            
        except Exception as e:
            logger.error("Failed to extract deployment records", error=str(e))
            return []
    
    async def _parse_deployment_content(self, page: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse deployment content to extract structured data"""
        try:
            content = page['body']['storage']['value']
            clean_text = self._clean_html_content(content)
            
            # Extract deployment entries
            deployment_entries = self._extract_deployment_entries(clean_text)
            
            if not deployment_entries:
                return None
            
            deployment_record = {
                'page_id': page['id'],
                'title': page['title'],
                'content': clean_text,
                'entries': deployment_entries,
                'raw_data': page
            }
            
            return deployment_record
            
        except Exception as e:
            logger.error("Failed to parse deployment content", 
                        page_id=page.get('id'), error=str(e))
            return None
    
    def _extract_deployment_entries(self, content: str) -> List[Dict[str, Any]]:
        """Extract individual deployment entries from content"""
        try:
            entries = []
            
            # Look for date patterns and associated deployments
            date_pattern = r'([A-Z][a-z]{2} \d{1,2}, \d{4})'
            lines = content.split('\n')
            
            current_date = None
            current_cases = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if line contains a date
                date_match = re.search(date_pattern, line)
                if date_match:
                    # Save previous entry if exists
                    if current_date and current_cases:
                        entries.append({
                            'date': current_date,
                            'cases': current_cases.copy()
                        })
                    
                    current_date = date_match.group(1)
                    current_cases = []
                
                # Check if line contains a JIRA key
                elif re.search(r'[A-Z]+-\d+', line):
                    case_info = self._parse_deployment_case(line)
                    if case_info:
                        current_cases.append(case_info)
            
            # Don't forget the last entry
            if current_date and current_cases:
                entries.append({
                    'date': current_date,
                    'cases': current_cases
                })
            
            return entries
            
        except Exception as e:
            logger.error("Failed to extract deployment entries", error=str(e))
            return []
    
    def _parse_deployment_case(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single deployment case line"""
        try:
            # Extract JIRA key
            jira_match = re.search(r'([A-Z]+-\d+)', line)
            if not jira_match:
                return None
            
            jira_key = jira_match.group(1)
            
            # Extract status (DONE, DEPLOYED TO PROD, etc.)
            status_match = re.search(r'(DONE|DEPLOYED TO PROD|FAILED)', line, re.IGNORECASE)
            status = status_match.group(1) if status_match else 'Unknown'
            
            # Extract notes (everything after the status)
            notes = line
            if status_match:
                notes = line[status_match.end():].strip()
            
            # Check for failure indicators
            has_failures = 'failed' in line.lower() or 'error' in line.lower()
            
            return {
                'jira_key': jira_key,
                'status': status,
                'notes': notes,
                'has_failures': has_failures,
                'raw_line': line
            }
            
        except Exception as e:
            logger.error("Failed to parse deployment case", line=line, error=str(e))
            return None
    
    def _extract_review_date(self, title: str, content: str) -> Optional[datetime]:
        """Extract review date from title or content"""
        try:
            # Try to find date in title first
            date_patterns = [
                r'(\d{1,2}/\d{1,2}/\d{4})',
                r'(\d{4}-\d{2}-\d{2})',
                r'([A-Z][a-z]{2} \d{1,2}, \d{4})'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, title)
                if match:
                    return self._parse_date_string(match.group(1))
            
            # Try content if title doesn't have date
            for pattern in date_patterns:
                match = re.search(pattern, content[:200])  # Check first 200 chars
                if match:
                    return self._parse_date_string(match.group(1))
            
            return None
            
        except Exception as e:
            logger.error("Failed to extract review date", error=str(e))
            return None
    
    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Parse various date string formats"""
        try:
            # Try different date formats
            formats = [
                '%m/%d/%Y',
                '%Y-%m-%d',
                '%b %d, %Y',
                '%B %d, %Y'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            return None
            
        except Exception as e:
            logger.error("Failed to parse date string", date_str=date_str, error=str(e))
            return None
    
    def _parse_confluence_date(self, date_str: str) -> Optional[datetime]:
        """Parse Confluence date string to datetime object"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception as e:
            logger.error("Failed to parse Confluence date", date_str=date_str, error=str(e))
            return None
    
    async def close(self):
        """Close the connector and clean up resources"""
        if self.http_client:
            await self.http_client.aclose()
        self.client = None