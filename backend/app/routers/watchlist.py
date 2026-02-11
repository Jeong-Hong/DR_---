"""관심종목 CRUD API 라우터"""
import logging
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Watchlist, DailyPrice
from app.schemas import WatchlistCreate, WatchlistResponse, WatchlistDetail, DailyPriceResponse, DashboardSummary
from app.services.kiwoom_client import kiwoom_client
from app.services.telegram_bot import send_enrollment_notification, send_removal_notification

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["watchlist"])


@router.post("/watchlist", response_model=WatchlistResponse, status_code=201)
async def create_watchlist(req: WatchlistCreate, db: AsyncSession = Depends(get_db)):
    stock_info = await kiwoom_client.search_stock_by_name(req.stock_name)
    if not stock_info:
        stock_info = await kiwoom_client.search_stock_by_code(req.stock_name)
    if not stock_info:
        raise HTTPException(status_code=404, detail=f"종목을 찾을 수 없습니다: {req.stock_name}")
    stock_code = stock_info["stock_code"]
    stock_name = stock_info["stock_name"]
    existing = await db.execute(select(Watchlist).where(Watchlist.stock_code == stock_code, Watchlist.status == "watching"))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"이미 관찰 중인 종목입니다: {stock_name}")
    d0_low_price = await kiwoom_client.get_current_low_price(stock_code)
    if not d0_low_price:
        raise HTTPException(status_code=502, detail="당일 시세를 조회할 수 없습니다")
    watchlist = Watchlist(stock_code=stock_code, stock_name=stock_name, enrolled_date=date.today(), d0_low_price=d0_low_price, status="watching")
    db.add(watchlist)
    await db.flush()
    await db.refresh(watchlist)
    await send_enrollment_notification(stock_name=stock_name, stock_code=stock_code, enrolled_date=watchlist.enrolled_date, d0_low_price=d0_low_price)
    return watchlist


@router.get("/watchlist", response_model=list[WatchlistResponse])
async def list_watchlist(status: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)):
    query = select(Watchlist).order_by(Watchlist.created_at.desc())
    if status:
        query = query.where(Watchlist.status == status)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/watchlist/{stock_code}", response_model=WatchlistDetail)
async def get_watchlist_detail(stock_code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Watchlist).where(Watchlist.stock_code == stock_code).order_by(Watchlist.created_at.desc()).limit(1))
    watchlist = result.scalar_one_or_none()
    if not watchlist:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다")
    prices_result = await db.execute(select(DailyPrice).where(DailyPrice.stock_code == stock_code).order_by(DailyPrice.trade_date.asc()))
    return WatchlistDetail(watchlist=watchlist, daily_prices=list(prices_result.scalars().all()))


@router.delete("/watchlist/{stock_code}")
async def delete_watchlist(stock_code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Watchlist).where(Watchlist.stock_code == stock_code, Watchlist.status == "watching"))
    watchlist = result.scalar_one_or_none()
    if not watchlist:
        raise HTTPException(status_code=404, detail="관찰 중인 해당 종목이 없습니다")
    watchlist.status = "expired"
    watchlist.updated_at = datetime.now()
    await db.commit()
    await send_removal_notification(stock_name=watchlist.stock_name, stock_code=watchlist.stock_code)
    return {"message": f"{watchlist.stock_name} 관찰 종료됨"}


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    watching = (await db.execute(select(func.count()).select_from(Watchlist).where(Watchlist.status == "watching"))).scalar() or 0
    alerted = (await db.execute(select(func.count()).select_from(Watchlist).where(Watchlist.status == "alerted"))).scalar() or 0
    expired = (await db.execute(select(func.count()).select_from(Watchlist).where(Watchlist.status == "expired"))).scalar() or 0
    total = (await db.execute(select(func.count()).select_from(Watchlist))).scalar() or 0
    avg_peak_v = (await db.execute(select(func.avg(Watchlist.peak_rate)))).scalar()
    finished = alerted + expired
    success_rate = round((alerted / finished) * 100, 1) if finished > 0 else None
    return DashboardSummary(watching_count=watching, alerted_count=alerted, expired_count=expired, total_count=total, avg_peak_rate=round(avg_peak_v, 2) if avg_peak_v else None, alert_success_rate=success_rate)


@router.get("/dashboard/history", response_model=list[WatchlistResponse])
async def get_history(status: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)):
    query = select(Watchlist).where(Watchlist.status.in_(["alerted", "expired"])).order_by(Watchlist.updated_at.desc())
    if status and status in ("alerted", "expired"):
        query = select(Watchlist).where(Watchlist.status == status).order_by(Watchlist.updated_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


@router.delete("/history/{record_id}")
async def delete_history(record_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Watchlist).where(Watchlist.id == record_id, Watchlist.status.in_(["alerted", "expired"])))
    watchlist = result.scalar_one_or_none()
    if not watchlist:
        raise HTTPException(status_code=404, detail="해당 이력을 찾을 수 없습니다")
    from sqlalchemy import delete as sql_delete
    await db.execute(sql_delete(DailyPrice).where(DailyPrice.stock_code == watchlist.stock_code))
    stock_name = watchlist.stock_name
    await db.delete(watchlist)
    await db.commit()
    return {"message": f"{stock_name} 이력이 삭제되었습니다"}
