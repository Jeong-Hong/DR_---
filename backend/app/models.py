"""SQLAlchemy 모델 정의"""
from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Index
from sqlalchemy.sql import func
from app.database import Base


class Watchlist(Base):
    __tablename__ = "watchlist"
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String, nullable=False, index=True)
    stock_name = Column(String, nullable=False)
    enrolled_date = Column(Date, nullable=False)
    d0_low_price = Column(Integer, nullable=False)
    status = Column(String, default="watching", index=True)
    alerted_at = Column(DateTime, nullable=True)
    alert_day = Column(Integer, nullable=True)
    peak_rate = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class DailyPrice(Base):
    __tablename__ = "daily_prices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String, nullable=False, index=True)
    trade_date = Column(Date, nullable=False)
    open_price = Column(Integer, nullable=True)
    high_price = Column(Integer, nullable=True)
    low_price = Column(Integer, nullable=True)
    close_price = Column(Integer, nullable=True)
    volume = Column(Integer, nullable=True)
    day_index = Column(Integer, nullable=True)
    change_rate = Column(Float, nullable=True)
    __table_args__ = (
        Index("ix_daily_code_date", "stock_code", "trade_date", unique=True),
    )
