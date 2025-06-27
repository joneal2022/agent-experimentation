"""
ChromaDB Manager for vector storage and semantic search
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
import uuid
import json
from datetime import datetime

from config import settings
from utils.logging import get_logger

logger = get_logger(__name__)


class ChromaDBManager:
    """Manager for ChromaDB operations and vector storage"""
    
    def __init__(self):
        self.client = None
        self.embedding_model = None
        self.collections = {}
        
    async def initialize(self):
        """Initialize ChromaDB client and embedding model"""
        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=settings.database.chromadb_path,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Initialize embedding model
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Initialize collections
            await self._initialize_collections()
            
            logger.info("ChromaDB manager initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize ChromaDB manager", error=str(e))
            raise
    
    async def _initialize_collections(self):
        """Initialize all required collections"""
        collection_configs = {
            "jira_tickets": {
                "description": "JIRA ticket content for semantic search",
                "metadata": {"type": "jira_content"}
            },
            "jira_comments": {
                "description": "JIRA comments for sentiment and issue analysis",
                "metadata": {"type": "jira_comments"}
            },
            "confluence_pages": {
                "description": "Confluence page content for knowledge search",
                "metadata": {"type": "confluence_content"}
            },
            "case_reviews": {
                "description": "Case review content for pattern analysis",
                "metadata": {"type": "case_reviews"}
            },
            "deployment_records": {
                "description": "Deployment records for failure analysis",
                "metadata": {"type": "deployment_records"}
            },
            "executive_insights": {
                "description": "AI-generated executive insights and summaries",
                "metadata": {"type": "executive_insights"}
            }
        }
        
        for collection_name, config in collection_configs.items():
            try:
                # Try to get existing collection
                collection = self.client.get_collection(collection_name)
                self.collections[collection_name] = collection
                logger.info(f"Loaded existing collection: {collection_name}")
                
            except ValueError:
                # Create new collection if it doesn't exist
                collection = self.client.create_collection(
                    name=collection_name,
                    metadata=config["metadata"]
                )
                self.collections[collection_name] = collection
                logger.info(f"Created new collection: {collection_name}")
    
    async def add_jira_tickets(self, tickets: List[Dict[str, Any]]) -> int:
        """Add JIRA tickets to vector storage"""
        try:
            if not tickets:
                return 0
            
            collection = self.collections["jira_tickets"]
            
            documents = []
            metadatas = []
            ids = []
            
            for ticket in tickets:
                # Create comprehensive text for embedding
                text_content = self._create_ticket_text(ticket)
                
                # Prepare metadata
                metadata = {
                    "ticket_key": ticket.get("ticket_key", ""),
                    "project": ticket.get("project_key", ""),
                    "status": ticket.get("status", ""),
                    "priority": ticket.get("priority", ""),
                    "assignee": ticket.get("assignee", ""),
                    "is_stalled": ticket.get("is_stalled", False),
                    "is_overdue": ticket.get("is_overdue", False),
                    "level_ii_failed": ticket.get("level_ii_failed", False),
                    "days_in_status": ticket.get("days_in_current_status", 0),
                    "created_date": ticket.get("created_date", "").isoformat() if ticket.get("created_date") else "",
                    "updated_date": ticket.get("updated_date", "").isoformat() if ticket.get("updated_date") else "",
                    "type": "jira_ticket"
                }
                
                documents.append(text_content)
                metadatas.append(metadata)
                ids.append(f"jira_ticket_{ticket.get('ticket_key', uuid.uuid4().hex)}")
            
            # Generate embeddings
            embeddings = self.embedding_model.encode(documents).tolist()
            
            # Add to collection
            collection.upsert(
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
                ids=ids
            )
            
            logger.info("Added JIRA tickets to vector storage", count=len(tickets))
            return len(tickets)
            
        except Exception as e:
            logger.error("Failed to add JIRA tickets to vector storage", error=str(e))
            return 0
    
    def _create_ticket_text(self, ticket: Dict[str, Any]) -> str:
        """Create comprehensive text representation of a ticket"""
        parts = []
        
        if ticket.get("summary"):
            parts.append(f"Summary: {ticket['summary']}")
        
        if ticket.get("description"):
            parts.append(f"Description: {ticket['description']}")
        
        if ticket.get("status"):
            parts.append(f"Status: {ticket['status']}")
        
        if ticket.get("priority"):
            parts.append(f"Priority: {ticket['priority']}")
        
        if ticket.get("assignee"):
            parts.append(f"Assignee: {ticket['assignee']}")
        
        # Add analysis flags
        flags = []
        if ticket.get("is_stalled"):
            flags.append("stalled work")
        if ticket.get("is_overdue"):
            flags.append("overdue")
        if ticket.get("level_ii_failed"):
            flags.append("level ii test failed")
        
        if flags:
            parts.append(f"Issues: {', '.join(flags)}")
        
        return " | ".join(parts)
    
    async def add_jira_comments(self, comments: List[Dict[str, Any]]) -> int:
        """Add JIRA comments to vector storage for sentiment analysis"""
        try:
            if not comments:
                return 0
            
            collection = self.collections["jira_comments"]
            
            documents = []
            metadatas = []
            ids = []
            
            for comment in comments:
                # Use comment body as document
                text_content = comment.get("body", "")
                if not text_content:
                    continue
                
                metadata = {
                    "comment_id": comment.get("comment_id", ""),
                    "ticket_key": comment.get("ticket_key", ""),
                    "author": comment.get("author", ""),
                    "created_date": comment.get("created_date", "").isoformat() if comment.get("created_date") else "",
                    "sentiment_score": comment.get("sentiment_score", ""),
                    "contains_blocker": comment.get("contains_blocker", False),
                    "type": "jira_comment"
                }
                
                documents.append(text_content)
                metadatas.append(metadata)
                ids.append(f"jira_comment_{comment.get('comment_id', uuid.uuid4().hex)}")
            
            if documents:
                embeddings = self.embedding_model.encode(documents).tolist()
                
                collection.upsert(
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embeddings,
                    ids=ids
                )
            
            logger.info("Added JIRA comments to vector storage", count=len(documents))
            return len(documents)
            
        except Exception as e:
            logger.error("Failed to add JIRA comments to vector storage", error=str(e))
            return 0
    
    async def add_confluence_pages(self, pages: List[Dict[str, Any]]) -> int:
        """Add Confluence pages to vector storage"""
        try:
            if not pages:
                return 0
            
            collection = self.collections["confluence_pages"]
            
            documents = []
            metadatas = []
            ids = []
            
            for page in pages:
                text_content = page.get("content", "")
                if not text_content:
                    continue
                
                metadata = {
                    "page_id": page.get("page_id", ""),
                    "space_key": page.get("space_key", ""),
                    "title": page.get("title", ""),
                    "author": page.get("author", ""),
                    "content_type": page.get("content_type", ""),
                    "created_date": page.get("created_date", "").isoformat() if page.get("created_date") else "",
                    "updated_date": page.get("updated_date", "").isoformat() if page.get("updated_date") else "",
                    "type": "confluence_page"
                }
                
                documents.append(text_content)
                metadatas.append(metadata)
                ids.append(f"confluence_page_{page.get('page_id', uuid.uuid4().hex)}")
            
            if documents:
                embeddings = self.embedding_model.encode(documents).tolist()
                
                collection.upsert(
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embeddings,
                    ids=ids
                )
            
            logger.info("Added Confluence pages to vector storage", count=len(documents))
            return len(documents)
            
        except Exception as e:
            logger.error("Failed to add Confluence pages to vector storage", error=str(e))
            return 0
    
    async def add_case_reviews(self, case_reviews: List[Dict[str, Any]]) -> int:
        """Add case reviews to vector storage for pattern analysis"""
        try:
            if not case_reviews:
                return 0
            
            collection = self.collections["case_reviews"]
            
            documents = []
            metadatas = []
            ids = []
            
            for review in case_reviews:
                # Create comprehensive text from case review
                text_content = self._create_case_review_text(review)
                
                metadata = {
                    "page_id": review.get("page_id", ""),
                    "review_date": review.get("review_date", "").isoformat() if review.get("review_date") else "",
                    "total_cases": review.get("total_cases", 0),
                    "critical_count": review.get("critical_count", 0),
                    "blocked_count": review.get("blocked_count", 0),
                    "stalled_count": review.get("stalled_count", 0),
                    "type": "case_review"
                }
                
                documents.append(text_content)
                metadatas.append(metadata)
                ids.append(f"case_review_{review.get('page_id', uuid.uuid4().hex)}")
            
            if documents:
                embeddings = self.embedding_model.encode(documents).tolist()
                
                collection.upsert(
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embeddings,
                    ids=ids
                )
            
            logger.info("Added case reviews to vector storage", count=len(documents))
            return len(documents)
            
        except Exception as e:
            logger.error("Failed to add case reviews to vector storage", error=str(e))
            return 0
    
    def _create_case_review_text(self, review: Dict[str, Any]) -> str:
        """Create text representation of case review"""
        parts = []
        
        # Add summary statistics
        parts.append(f"Total Cases: {review.get('total_cases', 0)}")
        parts.append(f"Critical Cases: {review.get('critical_count', 0)}")
        parts.append(f"Blocked Cases: {review.get('blocked_count', 0)}")
        parts.append(f"Stalled Cases: {review.get('stalled_count', 0)}")
        
        # Add case details
        sections = [
            "critical_cases", "high_urgency_cases", "blocked_cases",
            "waiting_on_client_cases", "internal_testing_cases"
        ]
        
        for section in sections:
            cases = review.get(section, [])
            if cases:
                section_text = f"{section.replace('_', ' ').title()}: "
                case_summaries = []
                for case in cases:
                    case_text = f"{case.get('jira_key', '')} ({case.get('priority', '')}) - {case.get('notes', '')}"
                    case_summaries.append(case_text)
                section_text += "; ".join(case_summaries[:3])  # Limit for text length
                parts.append(section_text)
        
        return " | ".join(parts)
    
    async def semantic_search(self, query: str, collection_name: str, 
                            filters: Optional[Dict[str, Any]] = None, 
                            limit: int = 10) -> List[Dict[str, Any]]:
        """Perform semantic search across specified collection"""
        try:
            collection = self.collections.get(collection_name)
            if not collection:
                logger.error(f"Collection not found: {collection_name}")
                return []
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query]).tolist()[0]
            
            # Prepare where clause for filtering
            where_clause = filters if filters else {}
            
            # Perform search
            results = collection.query(
                query_embeddings=[query_embedding],
                where=where_clause,
                n_results=limit,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            search_results = []
            for i in range(len(results["documents"][0])):
                result = {
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "similarity_score": 1 - results["distances"][0][i]  # Convert distance to similarity
                }
                search_results.append(result)
            
            logger.info("Semantic search completed", 
                       query=query, 
                       collection=collection_name, 
                       results_count=len(search_results))
            
            return search_results
            
        except Exception as e:
            logger.error("Semantic search failed", 
                        query=query, 
                        collection=collection_name, 
                        error=str(e))
            return []
    
    async def find_similar_issues(self, ticket_key: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar issues to a given ticket"""
        try:
            # First, get the original ticket
            ticket_results = await self.semantic_search(
                query=f"ticket_key:{ticket_key}",
                collection_name="jira_tickets",
                limit=1
            )
            
            if not ticket_results:
                return []
            
            original_ticket = ticket_results[0]
            
            # Search for similar tickets
            similar_tickets = await self.semantic_search(
                query=original_ticket["document"],
                collection_name="jira_tickets",
                filters={"ticket_key": {"$ne": ticket_key}},  # Exclude original ticket
                limit=limit
            )
            
            return similar_tickets
            
        except Exception as e:
            logger.error("Failed to find similar issues", 
                        ticket_key=ticket_key, error=str(e))
            return []
    
    async def find_problematic_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Find patterns in problematic tickets and comments"""
        try:
            patterns = {}
            
            # Find stalled tickets
            stalled_tickets = await self.semantic_search(
                query="blocked delayed stalled waiting",
                collection_name="jira_tickets",
                filters={"is_stalled": True},
                limit=20
            )
            patterns["stalled_patterns"] = stalled_tickets
            
            # Find failed testing patterns
            failed_tests = await self.semantic_search(
                query="test failed error bug defect",
                collection_name="jira_tickets",
                filters={"level_ii_failed": True},
                limit=20
            )
            patterns["testing_failure_patterns"] = failed_tests
            
            # Find negative sentiment comments
            negative_comments = await self.semantic_search(
                query="problem issue blocked stuck error failed",
                collection_name="jira_comments",
                filters={"contains_blocker": True},
                limit=20
            )
            patterns["negative_sentiment_patterns"] = negative_comments
            
            return patterns
            
        except Exception as e:
            logger.error("Failed to find problematic patterns", error=str(e))
            return {}
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics for all collections"""
        try:
            stats = {}
            
            for name, collection in self.collections.items():
                try:
                    count = collection.count()
                    stats[name] = {
                        "document_count": count,
                        "last_updated": datetime.utcnow().isoformat()
                    }
                except Exception as e:
                    stats[name] = {
                        "document_count": 0,
                        "error": str(e)
                    }
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get collection stats", error=str(e))
            return {}
    
    async def close(self):
        """Close ChromaDB connections"""
        try:
            # ChromaDB client doesn't need explicit closing
            self.client = None
            self.collections = {}
            logger.info("ChromaDB manager closed")
        except Exception as e:
            logger.error("Error closing ChromaDB manager", error=str(e))