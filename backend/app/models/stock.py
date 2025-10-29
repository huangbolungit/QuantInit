#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票相关数据模型
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class Stock(Base):
    """股票基础信息表"""
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    sector = Column(String(50))  # 板块
    industry = Column(String(100))  # 行业
    market = Column(String(20))  # 市场：SZ/SH
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联关系
    pool_entries = relationship("StockPool", back_populates="stock")
    factor_scores = relationship("FactorScore", back_populates="stock")
    suggestions = relationship("Suggestion", back_populates="stock")
    trades = relationship("SimulatedTrade", back_populates="stock")

    def __repr__(self):
        return f"<Stock({self.code} {self.name})>"


class StockPool(Base):
    """股票池表"""
    __tablename__ = "stock_pool"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    removed_at = Column(DateTime(timezone=True), nullable=True)
    current_score = Column(Float)
    entry_reason = Column(Text)
    exit_reason = Column(Text)
    status = Column(String(20), default="active")  # active, removed

    # 关联关系
    stock = relationship("Stock", back_populates="pool_entries")

    def __repr__(self):
        return f"<StockPool(stock_id={self.stock_id}, score={self.current_score})>"


class FactorScore(Base):
    """因子评分表"""
    __tablename__ = "factor_scores"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    date = Column(Date, nullable=False)
    momentum_score = Column(Float)  # 动量因子得分
    sentiment_score = Column(Float)  # 情绪因子得分
    value_score = Column(Float)  # 价值因子得分
    quality_score = Column(Float)  # 质量因子得分
    total_score = Column(Float)  # 综合得分
    raw_data = Column(JSON)  # 原始计算数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联关系
    stock = relationship("Stock", back_populates="factor_scores")

    # 复合唯一约束
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<FactorScore(stock_id={self.stock_id}, total={self.total_score})>"


class Suggestion(Base):
    """调仓建议表"""
    __tablename__ = "suggestions"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    action = Column(String(10), nullable=False)  # ADD, REMOVE
    reason = Column(Text, nullable=False)
    score = Column(Float)
    key_factors = Column(JSON)  # 关键影响因子
    status = Column(String(20), default="pending")  # pending, confirmed, ignored
    user_action = Column(String(20))  # 用户操作
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # 关联关系
    stock = relationship("Stock", back_populates="suggestions")

    def __repr__(self):
        return f"<Suggestion(stock_id={self.stock_id}, action={self.action})>"


class MarketData(Base):
    """市场数据缓存表"""
    __tablename__ = "market_cache"

    id = Column(Integer, primary_key=True, index=True)
    data_type = Column(String(50), nullable=False)  # overview, sectors, news
    data = Column(JSON, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<MarketData(type={self.data_type}, expires={self.expires_at})>"


class NewsAnalysis(Base):
    """新闻分析表"""
    __tablename__ = "news_analysis"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    summary = Column(Text)
    sentiment = Column(String(20))  # positive, negative, neutral
    related_sectors = Column(JSON)  # 关联板块
    related_stocks = Column(JSON)  # 关联股票
    impact_score = Column(Float)  # 影响程度评分
    ai_analysis = Column(JSON)  # AI分析结果
    published_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<NewsAnalysis(title={self.title[:50]}..., sentiment={self.sentiment})>"


class SimulatedTrade(Base):
    """模拟交易记录表"""
    __tablename__ = "simulated_trades"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    action = Column(String(10), nullable=False)  # BUY, SELL
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    total_amount = Column(Float, nullable=False)
    reason = Column(Text)
    status = Column(String(20), default="pending")  # pending, executed, cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    executed_at = Column(DateTime(timezone=True), nullable=True)

    # 关联关系
    stock = relationship("Stock", back_populates="trades")

    def __repr__(self):
        return f"<SimulatedTrade(stock_id={self.stock_id}, action={self.action}, amount={self.total_amount})>"