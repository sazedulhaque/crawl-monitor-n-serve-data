import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from apps.crawler.book_scraper_service import BookScrapingService

# Create scheduler instance (will be started by main.py)
scheduler = AsyncIOScheduler()
logger = logging.getLogger(__name__)


async def scheduled_for_book_scraping():
    """Example scheduled job 1"""
    # Trigger book scraping
    scraping_service = BookScrapingService()
    scraping_result = await scraping_service.start_scraping()
    logger.info(f"scraping_status: {scraping_result}")
    # Your scheduled job logic here


def schedule_for_sending_notifications():
    """Example scheduled job 2"""
    # logger.info("Executing scheduled job 2... (1 minutes interval)")
    # Your scheduled job logic here
    pass


async def start_scheduler():
    """Start the scheduler with configured jobs"""
    logger.info("Initializing scheduler...")

    # Add scheduled jobs
    scheduler.add_job(
        scheduled_for_book_scraping,
        IntervalTrigger(hours=1),
        id="job_1",
        name="Scheduled for book scraping",
        replace_existing=True,
    )

    # scheduler.add_job(
    #     schedule_for_sending_notifications,
    #     IntervalTrigger(minutes=1),
    #     id="job_2",
    #     name="Scheduled for sending Notifications",
    #     replace_existing=True,
    # )

    # Start the scheduler
    scheduler.start()
    logger.info("Scheduler started successfully")
    logger.info(f"Active jobs: {len(scheduler.get_jobs())}")


async def stop_scheduler():
    """Stop the scheduler gracefully"""
    logger.info("Shutting down scheduler...")
    scheduler.shutdown()
    logger.info(" Scheduler stopped successfully")
