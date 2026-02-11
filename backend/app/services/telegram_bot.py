"""텔레그램 알림 서비스 — 멀티 채널 지원"""
import logging
from datetime import date
from typing import List
from telegram import Bot
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _format_price(price: int) -> str:
    return f"{price:,}"


def _get_chat_ids() -> List[str]:
    raw = settings.telegram_chat_id or ""
    return [cid.strip() for cid in raw.split(",") if cid.strip()]


async def _send_to_all(message: str):
    if not settings.telegram_bot_token:
        return
    chat_ids = _get_chat_ids()
    if not chat_ids:
        return
    bot = Bot(token=settings.telegram_bot_token)
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"텔레그램 전송 실패 (chat_id={chat_id}): {e}")


async def send_alert(stock_name, stock_code, enrolled_date, d0_low_price, close_price, change_rate, day_index):
    message = (
        f"🚀 *관심종목 알림!*\n\n"
        f"📌 종목: *{stock_name}* ({stock_code})\n"
        f"📅 편입일: {enrolled_date}\n"
        f"📉 D-0 저가: {_format_price(d0_low_price)}원\n"
        f"📈 오늘 종가: {_format_price(close_price)}원\n"
        f"🔥 상승률: *+{change_rate:.2f}%*\n"
        f"📆 달성일차: D+{day_index}\n"
    )
    await _send_to_all(message)


async def send_enrollment_notification(stock_name, stock_code, enrolled_date, d0_low_price):
    target_price = int(d0_low_price * 1.5)
    message = (
        f"📌 *관심종목 편입!*\n\n"
        f"📍 종목: *{stock_name}* ({stock_code})\n"
        f"📅 편입일: {enrolled_date}\n"
        f"📉 D-0 저가: {_format_price(d0_low_price)}원\n"
        f"🎯 목표가 (50%): {_format_price(target_price)}원\n"
        f"⏳ 관찰기간: 5영업일\n"
    )
    await _send_to_all(message)


async def send_expiration_notification(stock_name, stock_code, enrolled_date, d0_low_price, peak_rate, watch_days):
    message = (
        f"⏰ *관심종목 편출 — 관찰기간 만료*\n\n"
        f"📍 종목: *{stock_name}* ({stock_code})\n"
        f"📅 편입일: {enrolled_date}\n"
        f"📉 D-0 저가: {_format_price(d0_low_price)}원\n"
        f"📊 기간 내 최고 상승률: *+{peak_rate:.2f}%*\n"
        f"📆 관찰일수: {watch_days}일\n"
        f"❌ 목표(50%) 미달성으로 편출\n"
    )
    await _send_to_all(message)


async def send_removal_notification(stock_name, stock_code):
    message = (
        f"🗑 *관심종목 편출 — 수동 삭제*\n\n"
        f"📍 종목: *{stock_name}* ({stock_code})\n"
        f"👤 사용자에 의해 관찰 종료\n"
    )
    await _send_to_all(message)


async def send_daily_summary(watching_count, alerted_today, expired_today):
    message = (
        f"📊 *일일 요약*\n\n"
        f"👀 관찰 중: {watching_count}종목\n"
        f"🚀 오늘 달성: {alerted_today}종목\n"
        f"⏰ 오늘 만료: {expired_today}종목\n"
    )
    await _send_to_all(message)
