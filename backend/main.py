#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股智能投顾助手 - FastAPI主应用
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from pathlib import Path

from app.core.config import settings
from app.core.database import engine, Base
from app.api.endpoints import market, stocks, pool, news, strategies
from app.api.websocket import router as websocket_router
from app.services.scoring.engine import ScoringEngine
from app.services.ai_analysis.glm46_client import GLM46Analyzer


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("A股智能投顾助手启动中...")

    # 确保SQLite数据库目录存在（CI/首次启动环境）
    try:
        if settings.DATABASE_URL.startswith("sqlite+aiosqlite"):
            db_path = settings.DATABASE_URL.split("///", 1)[-1]
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    # 创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 初始化服务
    scoring_engine = ScoringEngine()
    glm_analyzer = GLM46Analyzer()

    print("服务启动完成")

    yield

    # 关闭时执行
    print("应用关闭中...")
    await engine.dispose()
    print("服务已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="A股智能投顾助手 API",
    description="基于多因子综合评分模型的量化投顾工具",
    version="0.2.0-MVP",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vue.js开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(market.router, prefix="/api/market", tags=["市场数据"])
app.include_router(stocks.router, prefix="/api/stocks", tags=["股票信息"])
app.include_router(pool.router, prefix="/api/pool", tags=["股票池"])
app.include_router(news.router, prefix="/api/news", tags=["新闻分析"])
app.include_router(strategies.router, prefix="/api", tags=["策略管理"])
app.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])

# 静态文件服务
# app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "A股智能投顾助手 API",
        "version": "0.2.0-MVP",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "0.2.0-MVP",
        "services": {
            "database": "connected",
            "glm46": "configured" if settings.ANTHROPIC_AUTH_TOKEN else "not_configured"
        }
    }


if __name__ == "__main__":
    # 开发模式启动
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
