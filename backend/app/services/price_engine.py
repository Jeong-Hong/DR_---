"""가격 비교 엔진 — 50% 상승 감지 및 상태 관리"""
import logging
from datetime import date, datetime, timedelta
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Watchlist, DailyPrice
from app.config import get_settings
from app.services.kiwoom_client import kiwoom_client
from app.services.telegram_bot import send_alert, send_expiration_notification

logger = logging.getLogger(__name__)
settings = get_settings()


def _count_business_days(start_date: date, end_date: date) -> int:
    count = 0
    current = start_date + timedelta(days=1)
    while current <= end_date:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


async def process_daily_check(db: AsyncSession):
    today = date.today()
    result = await db.execute(select(Watchlist).where(Watchlist.status == "watching"))
    watching_stocks: List[Watchlist] = list(result.scalars().all())
    if not watching_stocks:
        logger.info("관찰 중인 종목 없음")
        return

    logger.info(f"관찰 종목 {len(watching_stocks)}개 시세 수집 시작")
    alerts_sent = 0
    expired_count = 0

    for stock in watching_stocks:
        try:
            day_index = _count_business_days(stock.enrolled_date, today)
            if day_index < 1:
                continue

            price_data = await kiwoom_client.get_daily_price(stock.stock_code, today)
            if not price_data:
                logger.warning(f"시세 조회 실패: {stock.stock_name}")
                continue

            close_price = price_data["close_price"]
            change_rate = ((close_price - stock.d0_low_price) / stock.d0_low_price) * 100

            daily = DailyPrice(
                stock_code=stock.stock_code, trade_date=today,
                open_price=price_data["open_price"], high_price=price_data["high_price"],
                low_price=price_data["low_price"], close_price=close_price,
                volume=price_data["volume"], day_index=day_index,
                change_rate=round(change_rate, 2),
            )
            db.add(daily)

            if change_rate > stock.peak_rate:
                stock.peak_rate = round(change_rate, 2)

            if change_rate >= settings.target_rate:
                stock.status = "alerted"
                stock.alert_day = day_index
                stock.alerted_at = datetime.now()
                stock.updated_at = datetime.now()
                alerts_sent += 1
                await send_alert(stock.stock_name, stock.stock_code, stock.enrolled_date,
                                 stock.d0_low_price, close_price, change_rate, day_index)
            elif day_index >= settings.watch_days:
                stock.status = "expired"
                stock.updated_at = datetime.now()
                expired_count += 1
                await send_expiration_notification(stock.stock_name, stock.stock_code,
                                                   stock.enrolled_date, stock.d0_low_price,
                                                   stock.peak_rate, day_index)
        except Exception as e:
            logger.error(f"종목 처리 오류: {stock.stock_name} - {e}")
            continue

    await db.commit()
    logger.info(f"일일 체크 완료: 알림 {alerts_sent}건, 만료 {expired_count}건")
