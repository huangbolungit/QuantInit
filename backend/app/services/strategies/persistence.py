#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略/信号持久化服务
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.strategy import Strategy, StrategySignal
from app.services.strategy_engine import StrategyConfig, TradingSignal


async def upsert_strategy(db: AsyncSession, cfg: StrategyConfig) -> None:
    row = await db.execute(select(Strategy).where(Strategy.id == cfg.id))
    existing = row.scalar_one_or_none()

    if existing is None:
        obj = Strategy(
            id=cfg.id,
            name=cfg.name,
            strategy_type=cfg.strategy_type,
            parameters=cfg.parameters,
            stock_pool=cfg.stock_pool,
            rebalance_frequency=cfg.rebalance_frequency,
            status=cfg.status.value,
            performance_metrics=cfg.performance_metrics,
            created_at=cfg.created_at,
            updated_at=cfg.updated_at,
            last_signal_time=cfg.last_signal_time,
        )
        db.add(obj)
    else:
        existing.name = cfg.name
        existing.strategy_type = cfg.strategy_type
        existing.parameters = cfg.parameters
        existing.stock_pool = cfg.stock_pool
        existing.rebalance_frequency = cfg.rebalance_frequency
        existing.status = cfg.status.value
        existing.performance_metrics = cfg.performance_metrics
        existing.updated_at = datetime.now()
        existing.last_signal_time = cfg.last_signal_time

    await db.commit()


async def save_signals(db: AsyncSession, signals: List[TradingSignal]) -> int:
    count = 0
    for s in signals:
        db.add(
            StrategySignal(
                id=s.id,
                strategy_id=s.strategy_id,
                stock_code=s.stock_code,
                signal_type=s.signal_type.value,
                confidence=s.confidence,
                price=s.price,
                timestamp=s.timestamp,
                reason=s.reason,
                expected_return=s.expected_return,
                risk_level=s.risk_level,
                parameters=s.parameters,
            )
        )
        count += 1
    await db.commit()
    return count


async def get_strategy(db: AsyncSession, strategy_id: str) -> Strategy | None:
    row = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    return row.scalar_one_or_none()


async def list_signals(
    db: AsyncSession, strategy_id: str, limit: int = 100, offset: int = 0
) -> List[StrategySignal]:
    q = (
        select(StrategySignal)
        .where(StrategySignal.strategy_id == strategy_id)
        .order_by(StrategySignal.timestamp.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = await db.execute(q)
    return list(rows.scalars().all())


async def list_latest_signals(
    db: AsyncSession, limit: int = 50, offset: int = 0, strategy_id: Optional[str] = None
) -> List[StrategySignal]:
    q = select(StrategySignal)
    if strategy_id:
        q = q.where(StrategySignal.strategy_id == strategy_id)
    q = q.order_by(StrategySignal.timestamp.desc()).limit(limit).offset(offset)
    rows = await db.execute(q)
    return list(rows.scalars().all())


async def touch_last_signal_time(db: AsyncSession, strategy_id: str, ts: datetime) -> None:
    row = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    obj = row.scalar_one_or_none()
    if obj:
        obj.last_signal_time = ts
        await db.commit()


async def delete_strategy(db: AsyncSession, strategy_id: str) -> bool:
    row = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    obj = row.scalar_one_or_none()
    if not obj:
        return False
    await db.delete(obj)
    await db.commit()
    return True
