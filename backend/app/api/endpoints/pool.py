#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票池API端点
"""

from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.stock import Stock, StockPool, FactorScore
from app.services.data_sources.manager import DataSourceManager
from app.services.scoring.engine import ScoringEngine

router = APIRouter()


def _serialize_pool_entry(stock: Stock, pool: StockPool, score: FactorScore | None) -> dict:
    """序列化股票池记录"""
    return {
        "stock": {
            "id": stock.id,
            "code": stock.code,
            "name": stock.name,
            "sector": stock.sector,
            "industry": stock.industry,
            "market": stock.market
        },
        "pool": {
            "id": pool.id,
            "status": pool.status,
            "current_score": pool.current_score,
            "entry_reason": pool.entry_reason,
            "exit_reason": pool.exit_reason,
            "added_at": pool.added_at.isoformat() if pool.added_at else None,
            "removed_at": pool.removed_at.isoformat() if pool.removed_at else None
        },
        "latest_score": {
            "date": score.date.isoformat() if score and score.date else None,
            "total_score": score.total_score if score else None
        }
    }


@router.get("/")
async def get_stock_pool(db: AsyncSession = Depends(get_db)):
    """获取当前股票池"""
    result = await db.execute(
        select(StockPool, Stock)
        .join(Stock, StockPool.stock_id == Stock.id)
        .where(StockPool.status == "active")
        .order_by(desc(StockPool.current_score))
    )

    items = []
    latest_timestamp = None
    for pool_entry, stock in result.all():
        score_result = await db.execute(
            select(FactorScore)
            .where(FactorScore.stock_id == stock.id)
            .order_by(desc(FactorScore.date))
            .limit(1)
        )
        latest_score = score_result.scalar_one_or_none()
        items.append(_serialize_pool_entry(stock, pool_entry, latest_score))
        if pool_entry.added_at:
            if latest_timestamp is None or pool_entry.added_at > latest_timestamp:
                latest_timestamp = pool_entry.added_at

    return {
        "pool": items,
        "total_count": len(items),
        "last_updated": latest_timestamp.isoformat() if latest_timestamp else None
    }


@router.post("/update")
async def update_stock_pool(db: AsyncSession = Depends(get_db)):
    """更新股票池评分"""
    result = await db.execute(
        select(StockPool, Stock)
        .join(Stock, StockPool.stock_id == Stock.id)
        .where(StockPool.status == "active")
    )
    rows: List[tuple[StockPool, Stock]] = result.all()
    if not rows:
        raise HTTPException(status_code=404, detail="当前没有活跃的股票池记录")

    manager = DataSourceManager()
    scoring_engine = ScoringEngine()
    today = date.today()
    updated = []

    try:
        for pool_entry, stock in rows:
            market_data = await manager.get_stock_quote(stock.code)
            if not market_data or market_data.get("error"):
                continue

            score_data = await scoring_engine.calculate_composite_score(
                stock.code,
                market_data,
                news_data=None
            )

            pool_entry.current_score = score_data.get("total_score")

            existing_score_result = await db.execute(
                select(FactorScore)
                .where(
                    FactorScore.stock_id == stock.id,
                    FactorScore.date == today
                )
                .limit(1)
            )
            factor_score = existing_score_result.scalar_one_or_none()

            if factor_score:
                factor_score.momentum_score = score_data.get("momentum_score")
                factor_score.sentiment_score = score_data.get("sentiment_score")
                factor_score.value_score = score_data.get("value_score")
                factor_score.quality_score = score_data.get("quality_score")
                factor_score.total_score = score_data.get("total_score")
                factor_score.raw_data = score_data
            else:
                factor_score = FactorScore(
                    stock_id=stock.id,
                    date=today,
                    momentum_score=score_data.get("momentum_score"),
                    sentiment_score=score_data.get("sentiment_score"),
                    value_score=score_data.get("value_score"),
                    quality_score=score_data.get("quality_score"),
                    total_score=score_data.get("total_score"),
                    raw_data=score_data
                )
                db.add(factor_score)

            updated.append({
                "stock_code": stock.code,
                "stock_name": stock.name,
                "score": score_data.get("total_score")
            })

        await db.commit()
    finally:
        await manager.close()

    return {
        "updated_count": len(updated),
        "updated": updated
    }


@router.get("/history")
async def get_pool_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """获取股票池历史记录"""
    result = await db.execute(
        select(StockPool, Stock)
        .join(Stock, StockPool.stock_id == Stock.id)
        .order_by(desc(StockPool.added_at))
        .limit(limit)
    )

    history = []
    for pool_entry, stock in result.all():
        history.append({
            "pool_id": pool_entry.id,
            "stock_code": stock.code,
            "stock_name": stock.name,
            "status": pool_entry.status,
            "current_score": pool_entry.current_score,
            "entry_reason": pool_entry.entry_reason,
            "exit_reason": pool_entry.exit_reason,
            "added_at": pool_entry.added_at.isoformat() if pool_entry.added_at else None,
            "removed_at": pool_entry.removed_at.isoformat() if pool_entry.removed_at else None
        })

    total_result = await db.execute(
        select(func.count(StockPool.id))
    )
    total_count = total_result.scalar() or 0

    return {
        "history": history,
        "total_count": total_count
    }
