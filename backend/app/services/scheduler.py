"""스케줄러 — 장 마감 후 자동 시세 수집"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.database import async_session
from app.services.price_engine import process_daily_check

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def _scheduled_daily_check():
    logger.info("⏰ 스케줄러 실행: 일일 시세 체크 시작")
    try:
        async with async_session() as db:
            await process_daily_check(db)
    except Exception as e:
        logger.error(f"스케줄러 실행 오류: {e}")


def start_scheduler():
    scheduler.add_job(
        _scheduled_daily_check,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour=20,
            minute=5,
            timezone="Asia/Seoul",
        ),
        id="daily_price_check",
        name="일일 시세 체크",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("📅 스케줄러 시작 — 평일 20:05 시세 체크 예약됨")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("스케줄러 종료")
