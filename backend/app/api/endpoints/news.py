#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻分析API端点
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.stock import NewsAnalysis

router = APIRouter()


def _serialize_news(item: NewsAnalysis) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "summary": item.summary,
        "sentiment": item.sentiment,
        "related_sectors": item.related_sectors,
        "related_stocks": item.related_stocks,
        "impact_score": item.impact_score,
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


@router.get("/")
async def get_news_list(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """获取新闻列表"""
    news_result = await db.execute(
        select(NewsAnalysis)
        .order_by(desc(NewsAnalysis.published_at), desc(NewsAnalysis.created_at))
        .offset(offset)
        .limit(limit)
    )
    items = news_result.scalars().all()

    count_result = await db.execute(
        select(func.count(NewsAnalysis.id))
    )
    total_count = count_result.scalar() or 0

    return {
        "news": [_serialize_news(item) for item in items],
        "total_count": total_count,
        "has_more": (offset + limit) < total_count
    }


@router.get("/{news_id}")
async def get_news_detail(
    news_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取新闻详情"""
    news = await db.get(NewsAnalysis, news_id)
    if not news:
        raise HTTPException(status_code=404, detail=f"未找到新闻 {news_id}")

    return _serialize_news(news)


@router.get("/sentiment/summary")
async def get_sentiment_summary(db: AsyncSession = Depends(get_db)):
    """获取情感分析摘要"""
    positive_result = await db.execute(
        select(func.count(NewsAnalysis.id)).where(NewsAnalysis.sentiment == "positive")
    )
    neutral_result = await db.execute(
        select(func.count(NewsAnalysis.id)).where(NewsAnalysis.sentiment == "neutral")
    )
    negative_result = await db.execute(
        select(func.count(NewsAnalysis.id)).where(NewsAnalysis.sentiment == "negative")
    )
    last_updated_result = await db.execute(
        select(func.max(NewsAnalysis.published_at))
    )

    positive = positive_result.scalar() or 0
    neutral = neutral_result.scalar() or 0
    negative = negative_result.scalar() or 0
    total = positive + neutral + negative

    overall_sentiment = "neutral"
    if total > 0:
        sentiment_score = (positive - negative) / total
        if sentiment_score > 0.2:
            overall_sentiment = "positive"
        elif sentiment_score < -0.2:
            overall_sentiment = "negative"

    last_updated = last_updated_result.scalar()

    return {
        "overall_sentiment": overall_sentiment,
        "positive_count": positive,
        "negative_count": negative,
        "neutral_count": neutral,
        "last_updated": last_updated.isoformat() if last_updated else None
    }
