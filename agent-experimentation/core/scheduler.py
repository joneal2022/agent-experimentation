"""
Task scheduler for data ingestion and processing
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import asyncio

from config import settings
from utils.logging import get_logger
from services.ingestion import JiraIngestionService, ConfluenceIngestionService, TempoIngestionService
from services.analysis import AnalysisOrchestrator
from services.alerts import AlertService

logger = get_logger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()


async def daily_data_ingestion():
    """Main daily data ingestion task"""
    try:
        logger.info("Starting daily data ingestion", 
                   timestamp=datetime.utcnow().isoformat())
        
        # Initialize services
        jira_service = JiraIngestionService()
        confluence_service = ConfluenceIngestionService()
        tempo_service = TempoIngestionService()
        analysis_orchestrator = AnalysisOrchestrator()
        alert_service = AlertService()
        
        # Step 1: Ingest data from all sources
        logger.info("Step 1: Starting data ingestion from all sources")
        
        # Run ingestion services in parallel
        ingestion_tasks = [
            jira_service.ingest_all_data(),
            confluence_service.ingest_all_data(),
            tempo_service.ingest_all_data()
        ]
        
        results = await asyncio.gather(*ingestion_tasks, return_exceptions=True)
        
        # Check for ingestion errors
        for i, result in enumerate(results):
            service_names = ["JIRA", "Confluence", "Tempo"]
            if isinstance(result, Exception):
                logger.error(f"{service_names[i]} ingestion failed", 
                           error=str(result))
            else:
                logger.info(f"{service_names[i]} ingestion completed", 
                           records_processed=result)
        
        # Step 2: Run AI analysis
        logger.info("Step 2: Starting AI analysis and processing")
        await analysis_orchestrator.run_daily_analysis()
        
        # Step 3: Generate and send alerts
        logger.info("Step 3: Processing alerts and notifications")
        await alert_service.process_daily_alerts()
        
        # Step 4: Generate executive summary
        logger.info("Step 4: Generating executive summary")
        await analysis_orchestrator.generate_executive_summary()
        
        logger.info("Daily data ingestion completed successfully")
        
    except Exception as e:
        logger.error("Daily data ingestion failed", error=str(e), exc_info=True)
        
        # Send critical alert about ingestion failure
        try:
            alert_service = AlertService()
            await alert_service.create_critical_alert(
                title="Daily Data Ingestion Failed",
                description=f"The daily data ingestion process failed with error: {str(e)}",
                alert_type="process_bottleneck"
            )
        except Exception as alert_error:
            logger.error("Failed to send ingestion failure alert", 
                        error=str(alert_error))


async def hourly_alert_check():
    """Hourly check for urgent alerts"""
    try:
        logger.info("Running hourly alert check")
        
        alert_service = AlertService()
        await alert_service.check_urgent_conditions()
        
        logger.info("Hourly alert check completed")
        
    except Exception as e:
        logger.error("Hourly alert check failed", error=str(e))


async def weekly_analytics():
    """Weekly analytics and reporting"""
    try:
        logger.info("Running weekly analytics")
        
        analysis_orchestrator = AnalysisOrchestrator()
        await analysis_orchestrator.generate_weekly_report()
        
        logger.info("Weekly analytics completed")
        
    except Exception as e:
        logger.error("Weekly analytics failed", error=str(e))


def start_scheduler():
    """Start the task scheduler"""
    try:
        # Parse ingestion time from settings
        hour, minute = map(int, settings.scheduling.ingestion_time.split(':'))
        
        # Schedule daily data ingestion
        scheduler.add_job(
            daily_data_ingestion,
            trigger=CronTrigger(
                hour=hour,
                minute=minute,
                timezone=settings.scheduling.timezone
            ),
            id='daily_ingestion',
            name='Daily Data Ingestion',
            replace_existing=True
        )
        
        # Schedule hourly alert checks
        scheduler.add_job(
            hourly_alert_check,
            trigger=CronTrigger(minute=0),  # Every hour at minute 0
            id='hourly_alerts',
            name='Hourly Alert Check',
            replace_existing=True
        )
        
        # Schedule weekly analytics (Mondays at 7 AM)
        scheduler.add_job(
            weekly_analytics,
            trigger=CronTrigger(
                day_of_week='mon',
                hour=7,
                minute=0,
                timezone=settings.scheduling.timezone
            ),
            id='weekly_analytics',
            name='Weekly Analytics',
            replace_existing=True
        )
        
        # Start the scheduler
        scheduler.start()
        
        logger.info("Scheduler started successfully",
                   daily_ingestion_time=settings.scheduling.ingestion_time,
                   timezone=settings.scheduling.timezone)
        
    except Exception as e:
        logger.error("Failed to start scheduler", error=str(e))
        raise


def stop_scheduler():
    """Stop the task scheduler"""
    try:
        scheduler.shutdown()
        logger.info("Scheduler stopped successfully")
    except Exception as e:
        logger.error("Failed to stop scheduler", error=str(e))


def get_scheduler_status():
    """Get current scheduler status and job information"""
    if not scheduler.running:
        return {"status": "stopped", "jobs": []}
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    
    return {
        "status": "running",
        "jobs": jobs
    }


# Manual trigger functions for testing/debugging
async def trigger_ingestion_now():
    """Manually trigger data ingestion (for testing)"""
    logger.info("Manually triggering data ingestion")
    await daily_data_ingestion()


async def trigger_alert_check_now():
    """Manually trigger alert check (for testing)"""
    logger.info("Manually triggering alert check")
    await hourly_alert_check()