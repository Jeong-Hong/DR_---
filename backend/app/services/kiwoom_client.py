"""키움증권 REST API 클라이언트 — 공식 문서 기반"""
import asyncio
import csv
import logging
import os
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

STOCK_NAME_MAP: Dict[str, str] = {}
STOCK_CODE_MAP: Dict[str, str] = {}


def _load_stock_csv():
    global STOCK_NAME_MAP, STOCK_CODE_MAP
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
    csv_files = ["kospi.csv", "kosdaq.csv"]
    total = 0
    for csv_file in csv_files:
        filepath = os.path.join(data_dir, csv_file)
        if not os.path.exists(filepath):
            logger.warning(f"CSV 파일 없음: {filepath}")
            continue
        for encoding in ["euc-kr", "cp949", "utf-8-sig", "utf-8"]:
            try:
                with open(filepath, "r", encoding=encoding) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        code = row.get("종목코드", "").strip()
                        name = row.get("종목명", "").strip()
                        if code and name:
                            STOCK_NAME_MAP[name] = code
                            STOCK_CODE_MAP[code] = name
                            total += 1
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
    logger.info(f"📋 전종목 로드 완료: {total}개")


_load_stock_csv()


class KiwoomClient:
    def __init__(self):
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._semaphore = asyncio.Semaphore(5)

    async def _ensure_token(self):
        if self._access_token and self._token_expires_at and datetime.now() < self._token_expires_at:
            return
        await self._get_access_token()

    async def _get_access_token(self):
        url = f"{settings.kiwoom_api_url}/oauth2/token"
        headers = {"Content-Type": "application/json;charset=UTF-8", "api-id": "au10001"}
        body = {"grant_type": "client_credentials", "appkey": settings.kiwoom_app_key, "secretkey": settings.kiwoom_secret_key}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if data.get("return_code") != 0:
                raise Exception(f"토큰 발급 실패: {data.get('return_msg')}")
            self._access_token = data["token"]
            expires_str = data.get("expires_dt", "")
            if expires_str and len(expires_str) >= 14:
                self._token_expires_at = datetime.strptime(expires_str, "%Y%m%d%H%M%S")
            else:
                self._token_expires_at = datetime.now() + timedelta(hours=23)

    async def _request(self, api_id: str, path: str, body: dict) -> dict:
        await self._ensure_token()
        headers = {"Content-Type": "application/json;charset=UTF-8", "api-id": api_id, "authorization": f"Bearer {self._access_token}"}
        async with self._semaphore:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(f"{settings.kiwoom_api_url}{path}", json=body, headers=headers)
                resp.raise_for_status()
                await asyncio.sleep(0.25)
                return resp.json()

    async def search_stock_by_name(self, stock_name: str) -> Optional[Dict[str, str]]:
        if stock_name in STOCK_NAME_MAP:
            return {"stock_code": STOCK_NAME_MAP[stock_name], "stock_name": stock_name}
        matches = [(n, c) for n, c in STOCK_NAME_MAP.items() if stock_name in n or n in stock_name]
        if len(matches) == 1:
            return {"stock_code": matches[0][1], "stock_name": matches[0][0]}
        elif len(matches) > 1:
            best = min(matches, key=lambda x: len(x[0]))
            return {"stock_code": best[1], "stock_name": best[0]}
        return None

    async def search_stock_by_code(self, stock_code: str) -> Optional[Dict[str, str]]:
        if stock_code in STOCK_CODE_MAP:
            return {"stock_code": stock_code, "stock_name": STOCK_CODE_MAP[stock_code]}
        try:
            data = await self._request("ka10001", "/api/dostk/stkinfo", {"stk_cd": stock_code})
            stk_nm = data.get("stk_nm", "").strip()
            if stk_nm:
                STOCK_NAME_MAP[stk_nm] = stock_code
                return {"stock_code": stock_code, "stock_name": stk_nm}
            return None
        except Exception as e:
            logger.error(f"종목코드 조회 실패: {stock_code} - {e}")
            return None

    async def get_stock_info(self, stock_code: str) -> Optional[Dict[str, Any]]:
        try:
            data = await self._request("ka10001", "/api/dostk/stkinfo", {"stk_cd": stock_code})
            return {
                "stock_code": data.get("stk_cd", stock_code),
                "stock_name": data.get("stk_nm", ""),
                "cur_price": self._parse_price(data.get("cur_prc", "0")),
                "open_price": self._parse_price(data.get("open_pric", "0")),
                "high_price": self._parse_price(data.get("high_pric", "0")),
                "low_price": self._parse_price(data.get("low_pric", "0")),
                "volume": int(data.get("trde_qty", "0") or "0"),
            }
        except Exception as e:
            logger.error(f"종목 기본정보 조회 실패: {stock_code} - {e}")
            return None

    async def get_daily_prices(self, stock_code: str) -> Optional[List[Dict[str, Any]]]:
        try:
            data = await self._request("ka10005", "/api/dostk/mrkcond", {"stk_cd": stock_code})
            records = data.get("stk_ddwkmm", [])
            if not records:
                return None
            result = []
            for rec in records:
                trade_date_str = rec.get("date", "")
                if not trade_date_str or len(trade_date_str) < 8:
                    continue
                result.append({
                    "trade_date": datetime.strptime(trade_date_str, "%Y%m%d").date(),
                    "open_price": self._parse_price(rec.get("open_pric", "0")),
                    "high_price": self._parse_price(rec.get("high_pric", "0")),
                    "low_price": self._parse_price(rec.get("low_pric", "0")),
                    "close_price": self._parse_price(rec.get("close_pric", "0")),
                    "volume": int(rec.get("trde_qty", "0") or "0"),
                })
            return result
        except Exception as e:
            logger.error(f"일별 시세 조회 실패: {stock_code} - {e}")
            return None

    async def get_daily_price(self, stock_code: str, target_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
        prices = await self.get_daily_prices(stock_code)
        if not prices:
            return None
        if target_date is None:
            return prices[0] if prices else None
        for p in prices:
            if p["trade_date"] == target_date:
                return p
        return prices[0] if prices else None

    async def get_current_low_price(self, stock_code: str) -> Optional[int]:
        info = await self.get_stock_info(stock_code)
        if info and info["low_price"] > 0:
            return info["low_price"]
        prices = await self.get_daily_prices(stock_code)
        if prices and len(prices) > 0:
            return prices[0]["low_price"]
        return None

    @staticmethod
    def _parse_price(value: str) -> int:
        if not value or value.strip() == "":
            return 0
        cleaned = value.strip().lstrip("+-")
        try:
            return int(cleaned)
        except ValueError:
            try:
                return int(float(cleaned))
            except ValueError:
                return 0


kiwoom_client = KiwoomClient()
