#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略管理API端点
提供策略的CRUD操作与信号生成功能。
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import logging

from app.core.database import get_db
from app.models.strategy import Strategy
import app.services.strategies.persistence as persistence
from app.services.strategy_engine import (
    get_strategy_engine,
    StrategyStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ===== Pydantic 模型 =====
class StrategyCreateRequest(BaseModel):
    name: str = Field(..., description="策略名称")
    strategy_type: str = Field(..., description="策略类型")
    parameters: Dict[str, Any] = Field(..., description="策略参数")
    stock_pool: List[str] = Field(..., description="股票池")
    rebalance_frequency: int = Field(default=10, description="调频周期(天)")


class StrategyUpdateRequest(BaseModel):
    parameters: Optional[Dict[str, Any]] = Field(None, description="策略参数")
    stock_pool: Optional[List[str]] = Field(None, description="股票池")
    status: Optional[StrategyStatus] = Field(None, description="策略状态")


class StrategyResponse(BaseModel):
    id: str
    name: str
    strategy_type: str
    parameters: Dict[str, Any]
    stock_pool: List[str]
    rebalance_frequency: int
    status: str
    created_at: str
    updated_at: str
    last_signal_time: Optional[str] = None
    performance_metrics: Dict[str, float]


class TradingSignalResponse(BaseModel):
    id: str
    strategy_id: str
    stock_code: str
    signal_type: str
    confidence: float
    price: Optional[float] = None
    timestamp: str
    reason: Optional[str] = ""
    expected_return: Optional[float] = 0.0
    risk_level: Optional[str] = ""


# ===== 策略 CRUD =====
@router.post("/strategies", response_model=StrategyResponse)
async def create_strategy(
    request: StrategyCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> StrategyResponse:
    try:
        engine = get_strategy_engine()

        strategy_id = await engine.create_strategy(
            name=request.name,
            strategy_type=request.strategy_type,
            parameters=request.parameters,
            stock_pool=request.stock_pool,
            rebalance_frequency=request.rebalance_frequency,
        )

        created_strategy = engine.active_strategies[strategy_id]

        # 持久化（失败不致命）
        try:
            await persistence.upsert_strategy(db, created_strategy)
        except Exception as perr:  # pragma: no cover - 容错
            logger.warning(f"策略持久化失败(忽略): {perr}")

        return StrategyResponse(
            id=created_strategy.id,
            name=created_strategy.name,
            strategy_type=created_strategy.strategy_type,
            parameters=created_strategy.parameters,
            stock_pool=created_strategy.stock_pool,
            rebalance_frequency=created_strategy.rebalance_frequency,
            status=created_strategy.status.value,
            created_at=created_strategy.created_at.isoformat(),
            updated_at=created_strategy.updated_at.isoformat(),
            last_signal_time=(
                created_strategy.last_signal_time.isoformat()
                if created_strategy.last_signal_time
                else None
            ),
            performance_metrics=created_strategy.performance_metrics,
        )
    except Exception as e:  # noqa: BLE001
        logger.error(f"创建策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建策略失败: {str(e)}")


@router.get("/strategies", response_model=List[StrategyResponse])
async def list_strategies(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> List[StrategyResponse]:
    # 参数校验
    if limit <= 0 or limit > 1000:
        raise HTTPException(status_code=400, detail="limit 必须在 1..1000 之间")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset 不能为负数")

    # DB 优先
    try:
        q = select(Strategy)
        if status:
            q = q.where(Strategy.status == status)
        q = q.order_by(Strategy.created_at.desc(), Strategy.id.asc()).limit(limit).offset(offset)
        rows = await db.execute(q)
        records = list(rows.scalars().all())
        if records:
            return [
                StrategyResponse(
                    id=r.id,
                    name=r.name,
                    strategy_type=r.strategy_type,
                    parameters=r.parameters or {},
                    stock_pool=r.stock_pool or [],
                    rebalance_frequency=r.rebalance_frequency,
                    status=r.status,
                    created_at=(
                        r.created_at.isoformat() if r.created_at else datetime.now().isoformat()
                    ),
                    updated_at=(
                        r.updated_at.isoformat() if r.updated_at else datetime.now().isoformat()
                    ),
                    last_signal_time=(r.last_signal_time.isoformat() if r.last_signal_time else None),
                    performance_metrics=r.performance_metrics or {},
                )
                for r in records
            ]
    except Exception as db_err:  # pragma: no cover - 容错
        logger.warning(f"读取策略列表DB失败，回退到内存: {db_err}")

    # 内存回退
    engine = get_strategy_engine()
    all_strategies = list(engine.active_strategies.values())
    if status:
        all_strategies = [s for s in all_strategies if s.status.value == status]
    sliced = all_strategies[offset : offset + limit]
    return [
        StrategyResponse(
            id=s.id,
            name=s.name,
            strategy_type=s.strategy_type,
            parameters=s.parameters,
            stock_pool=s.stock_pool,
            rebalance_frequency=s.rebalance_frequency,
            status=s.status.value,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
            last_signal_time=s.last_signal_time.isoformat() if s.last_signal_time else None,
            performance_metrics=s.performance_metrics,
        )
        for s in sliced
    ]


@router.get("/strategies/{strategy_id}", response_model=StrategyResponse)
async def get_strategy_detail(strategy_id: str, db: AsyncSession = Depends(get_db)) -> StrategyResponse:
    # DB 优先
    try:
        rec = await persistence.get_strategy(db, strategy_id)
        if rec:
            return StrategyResponse(
                id=rec.id,
                name=rec.name,
                strategy_type=rec.strategy_type,
                parameters=rec.parameters or {},
                stock_pool=rec.stock_pool or [],
                rebalance_frequency=rec.rebalance_frequency,
                status=rec.status,
                created_at=(rec.created_at.isoformat() if rec.created_at else datetime.now().isoformat()),
                updated_at=(rec.updated_at.isoformat() if rec.updated_at else datetime.now().isoformat()),
                last_signal_time=(rec.last_signal_time.isoformat() if rec.last_signal_time else None),
                performance_metrics=rec.performance_metrics or {},
            )
    except Exception as db_err:  # pragma: no cover
        logger.warning(f"读取策略详情DB失败，回退到内存: {db_err}")

    # 内存兜底
    engine = get_strategy_engine()
    s = engine.active_strategies.get(strategy_id)
    if not s:
        raise HTTPException(status_code=404, detail="策略不存在")
    return StrategyResponse(
        id=s.id,
        name=s.name,
        strategy_type=s.strategy_type,
        parameters=s.parameters,
        stock_pool=s.stock_pool,
        rebalance_frequency=s.rebalance_frequency,
        status=s.status.value,
        created_at=s.created_at.isoformat(),
        updated_at=s.updated_at.isoformat(),
        last_signal_time=s.last_signal_time.isoformat() if s.last_signal_time else None,
        performance_metrics=s.performance_metrics,
    )


@router.put("/strategies/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: str,
    request: StrategyUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> StrategyResponse:
    engine = get_strategy_engine()
    ok = await engine.update_strategy(
        strategy_id=strategy_id,
        parameters=request.parameters or {},
        stock_pool=request.stock_pool or None,
        status=request.status or None,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="策略不存在或更新失败")

    cfg = engine.active_strategies[strategy_id]
    try:
        await persistence.upsert_strategy(db, cfg)
    except Exception as perr:  # pragma: no cover
        logger.warning(f"更新后持久化失败(忽略): {perr}")

    return StrategyResponse(
        id=cfg.id,
        name=cfg.name,
        strategy_type=cfg.strategy_type,
        parameters=cfg.parameters,
        stock_pool=cfg.stock_pool,
        rebalance_frequency=cfg.rebalance_frequency,
        status=cfg.status.value,
        created_at=cfg.created_at.isoformat(),
        updated_at=cfg.updated_at.isoformat(),
        last_signal_time=cfg.last_signal_time.isoformat() if cfg.last_signal_time else None,
        performance_metrics=cfg.performance_metrics,
    )


@router.delete("/strategies/{strategy_id}")
async def delete_strategy(strategy_id: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    engine = get_strategy_engine()
    try:
        await persistence.delete_strategy(db, strategy_id)
    except Exception as perr:  # pragma: no cover
        logger.warning(f"DB 删除策略失败(忽略继续): {perr}")
    try:
        await engine.delete_strategy(strategy_id)
    except Exception as perr:  # pragma: no cover
        logger.warning(f"内存删除策略失败(忽略): {perr}")
    return {"success": True}


# ===== 信号相关 =====
@router.post("/signals/generate", response_model=List[TradingSignalResponse])
async def generate_all_signals(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> List[TradingSignalResponse]:
    try:
        engine = get_strategy_engine()
        signals = await engine.generate_signals()

        # 持久化（失败忽略）并更新策略最后信号时间
        try:
            if signals:
                await persistence.save_signals(db, signals)
                from collections import defaultdict

                latest_ts = defaultdict(datetime)
                for s in signals:
                    if s.timestamp and s.timestamp > latest_ts[s.strategy_id]:
                        latest_ts[s.strategy_id] = s.timestamp
                for sid, ts in latest_ts.items():
                    await persistence.touch_last_signal_time(db, sid, ts)
        except Exception as perr:  # pragma: no cover
            logger.warning(f"批量信号持久化失败(忽略): {perr}")

        return [
            TradingSignalResponse(
                id=s.id,
                strategy_id=s.strategy_id,
                stock_code=s.stock_code,
                signal_type=s.signal_type,
                confidence=s.confidence,
                price=s.price,
                timestamp=s.timestamp.isoformat(),
                reason=s.reason,
                expected_return=s.expected_return,
                risk_level=s.risk_level,
            )
            for s in signals
        ]
    except Exception as e:
        logger.error(f"批量生成交易信号失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量生成交易信号失败: {str(e)}")


@router.get("/signals/latest", response_model=List[TradingSignalResponse])
async def get_latest_signals(
    limit: int = 50,
    offset: int = 0,
    strategy_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> List[TradingSignalResponse]:
    if limit <= 0 or limit > 1000:
        raise HTTPException(status_code=400, detail="limit必须在1..1000之间")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset不能为负数")

    # DB 优先
    try:
        items = await persistence.list_latest_signals(
            db, limit=limit, offset=offset, strategy_id=strategy_id
        )
    except Exception as db_err:  # pragma: no cover
        logger.warning(f"获取最新信号DB失败，回退内存: {db_err}")
        items = []

    if items:
        return [
            TradingSignalResponse(
                id=s.id,
                strategy_id=s.strategy_id,
                stock_code=s.stock_code,
                signal_type=s.signal_type,
                confidence=s.confidence,
                price=s.price or 0.0,
                timestamp=s.timestamp.isoformat(),
                reason=s.reason or "",
                expected_return=s.expected_return or 0.0,
                risk_level=s.risk_level or "",
            )
            for s in items
        ]

    # 内存兜底
    engine = get_strategy_engine()
    all_signals = engine.signal_history
    if strategy_id:
        all_signals = [s for s in all_signals if s.strategy_id == strategy_id]
    latest_signals = sorted(all_signals, key=lambda x: x.timestamp, reverse=True)
    sliced = latest_signals[offset : offset + limit]
    return [
        TradingSignalResponse(
            id=s.id,
            strategy_id=s.strategy_id,
            stock_code=s.stock_code,
            signal_type=s.signal_type.value,
            confidence=s.confidence,
            price=s.price,
            timestamp=s.timestamp.isoformat(),
            reason=s.reason,
            expected_return=s.expected_return,
            risk_level=s.risk_level,
        )
        for s in sliced
    ]


logger.info("策略API路由加载完成")
