"""FastAPI 메인 엔트리포인트"""
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import init_db
from app.routers.watchlist import router as watchlist_router
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 관심종목 관리 시스템 시작")
    await init_db()
    start_scheduler()
    yield
    stop_scheduler()
    logger.info("관심종목 관리 시스템 종료")


app = FastAPI(title="키움 관심종목 관리 시스템", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(watchlist_router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "관심종목 관리 시스템 정상 운영 중"}


backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
frontend_path = os.path.join(backend_dir, "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
