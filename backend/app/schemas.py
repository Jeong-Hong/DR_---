"""Pydantic 스키마 — API 요청/응답 정의"""
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel


class WatchlistCreate(BaseModel):
    stock_name: str


class WatchlistResponse(BaseModel):
    id: int
    stock_code: str
    stock_name: str
    enrolled_date: date
    d0_low_price: int
    status: str
    alerted_at: Optional[datetime] = None
    alert_day: Optional[int] = None
    peak_rate: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class DailyPriceResponse(BaseModel):
    trade_date: date
    open_price: Optional[int] = None
    high_price: Optional[int] = None
    low_price: Optional[int] = None
    close_price: Optional[int] = None
    volume: Optional[int] = None
    day_index: Optional[int] = None
    change_rate: Optional[float] = None
    model_config = {"from_attributes": True}


class WatchlistDetail(BaseModel):
    watchlist: WatchlistResponse
    daily_prices: List[DailyPriceResponse] = []


class DashboardSummary(BaseModel):
    watching_count: int
    alerted_count: int
    expired_count: int
    total_count: int
    avg_peak_rate: Optional[float] = None
    alert_success_rate: Optional[float] = None
