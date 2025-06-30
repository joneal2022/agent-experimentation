"""
Database configuration and initialization
"""
import asyncio
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import redis
import chromadb
from chromadb.config import Settings as ChromaSettings

from config import settings
from utils.logging import get_logger

logger = get_logger(__name__)

# SQLAlchemy setup
engine = create_engine(settings.database.postgres_url, echo=settings.app.debug)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis setup
redis_client = redis.from_url(settings.database.redis_url, decode_responses=True)

# ChromaDB setup
chroma_client = chromadb.PersistentClient(
    path=settings.database.chromadb_path,
    settings=ChromaSettings(
        anonymized_telemetry=False,
        allow_reset=True
    )
)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_redis():
    """Get Redis client"""
    return redis_client


def get_chroma():
    """Get ChromaDB client"""
    return chroma_client


def get_db_url():
    """Get database URL for external connections"""
    return settings.database.postgres_url


async def init_db():
    """Initialize database tables"""
    try:
        logger.info("Initializing database...")
        
        # Import all models to ensure they're registered
        from models import jira, confluence, tempo, alerts
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Initialize ChromaDB collections
        try:
            chroma_client.get_collection("jira_tickets")
        except:
            chroma_client.create_collection(
                name="jira_tickets",
                metadata={"description": "JIRA ticket embeddings for semantic search"}
            )
        
        try:
            chroma_client.get_collection("confluence_pages")
        except:
            chroma_client.create_collection(
                name="confluence_pages", 
                metadata={"description": "Confluence page embeddings for semantic search"}
            )
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def test_connections():
    """Test all database connections"""
    try:
        # Test PostgreSQL
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("PostgreSQL connection successful")
        
        # Test Redis
        redis_client.ping()
        logger.info("Redis connection successful")
        
        # Test ChromaDB
        chroma_client.heartbeat()
        logger.info("ChromaDB connection successful")
        
        return True
        
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False