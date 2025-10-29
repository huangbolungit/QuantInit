#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票信息API端点
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.stock import Stock, FactorScore
from app.services.data_sources.manager import DataSourceManager

router = APIRouter()


def _serialize_stock(stock: Stock) -> dict:
    """将股票模型转换为可序列化字典"""
    return {
        "id": stock.id,
        "code": stock.code,
        "name": stock.name,
        "sector": stock.sector,
        "industry": stock.industry,
        "market": stock.market,
        "is_active": stock.is_active,
        "created_at": stock.created_at.isoformat() if stock.created_at else None,
        "updated_at": stock.updated_at.isoformat() if stock.updated_at else None,
    }


def _serialize_factor_score(score: FactorScore | None) -> dict | None:
    if not score:
        return None
    return {
        "id": score.id,
        "date": score.date.isoformat() if score.date else None,
        "momentum_score": score.momentum_score,
        "sentiment_score": score.sentiment_score,
        "value_score": score.value_score,
        "quality_score": score.quality_score,
        "total_score": score.total_score,
        "raw_data": score.raw_data,
        "created_at": score.created_at.isoformat() if score.created_at else None,
    }


@router.get("/{stock_code}")
async def get_stock_info(
    stock_code: str,
    db: AsyncSession = Depends(get_db)
):
    """获取股票基本信息"""
    result = await db.execute(select(Stock).where(Stock.code == stock_code))
    stock = result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail=f"未找到股票 {stock_code}")

    manager = DataSourceManager()
    try:
        market_quote = await manager.get_stock_quote(stock_code)
        if market_quote.get("error"):
            market_quote = {}
    finally:
        await manager.close()

    score_result = await db.execute(
        select(FactorScore)
        .where(FactorScore.stock_id == stock.id)
        .order_by(desc(FactorScore.date))
        .limit(1)
    )
    latest_score = score_result.scalar_one_or_none()

    return {
        "stock": _serialize_stock(stock),
        "market_data": market_quote,
        "latest_score": _serialize_factor_score(latest_score)
    }


@router.get("/{stock_code}/kline")
async def get_stock_kline(
    stock_code: str,
    period: str = "1d",
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """获取股票K线数据"""
    result = await db.execute(select(Stock.id).where(Stock.code == stock_code))
    stock_id = result.scalar_one_or_none()
    if not stock_id:
        raise HTTPException(status_code=404, detail=f"未找到股票 {stock_code}")

    manager = DataSourceManager()
    try:
        kline_data = await manager.get_kline_data(stock_code, period, limit)
    finally:
        await manager.close()

    return {
        "stock_code": stock_code,
        "period": period,
        "count": len(kline_data),
        "data": kline_data
    }


@router.get("/{stock_code}/factors")
async def get_stock_factors(
    stock_code: str,
    db: AsyncSession = Depends(get_db)
):
    """获取股票因子评分"""
    result = await db.execute(select(Stock).where(Stock.code == stock_code))
    stock = result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail=f"未找到股票 {stock_code}")

    score_result = await db.execute(
        select(FactorScore)
        .where(FactorScore.stock_id == stock.id)
        .order_by(desc(FactorScore.date))
        .limit(1)
    )
    latest_score = score_result.scalar_one_or_none()

    if not latest_score:
        return {
            "stock_code": stock_code,
            "factors": {
                "momentum": None,
                "sentiment": None,
                "value": None,
                "quality": None
            },
            "total_score": None,
            "date": None
        }

    return {
        "stock_code": stock_code,
        "factors": {
            "momentum": latest_score.momentum_score,
            "sentiment": latest_score.sentiment_score,
            "value": latest_score.value_score,
            "quality": latest_score.quality_score
        },
        "total_score": latest_score.total_score,
        "date": latest_score.date.isoformat() if latest_score.date else None
    }
