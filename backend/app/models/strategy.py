#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略与交易信号持久化模型
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Text,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    strategy_type = Column(String(50), nullable=False)
    parameters = Column(JSON, nullable=False)
    stock_pool = Column(JSON, nullable=False)
    rebalance_frequency = Column(Integer, nullable=False, default=10)
    status = Column(String(20), nullable=False, default="active")
    performance_metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    last_signal_time = Column(DateTime(timezone=True), nullable=True)

    signals = relationship("StrategySignal", back_populates="strategy", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Strategy({self.id}, {self.name}, {self.strategy_type})>"


class StrategySignal(Base):
    __tablename__ = "strategy_signals"

    id = Column(String(64), primary_key=True, index=True)
    strategy_id = Column(String(64), ForeignKey("strategies.id"), nullable=False, index=True)
    stock_code = Column(String(16), nullable=False, index=True)
    signal_type = Column(String(10), nullable=False)
    confidence = Column(Float, nullable=False)
    price = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    reason = Column(Text, nullable=True)
    expected_return = Column(Float, nullable=True)
    risk_level = Column(String(20), nullable=True)
    parameters = Column(JSON, nullable=True)

    strategy = relationship("Strategy", back_populates="signals")

    def __repr__(self) -> str:
        return f"<StrategySignal({self.id}, {self.strategy_id}, {self.stock_code}, {self.signal_type})>"

