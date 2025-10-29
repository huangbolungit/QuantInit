#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场数据API端点
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from app.core.database import get_db
from app.services.data_sources.eastmoney import EastmoneyClient
from app.services.data_sources.tencent import TencentClient
from app.services.data_sources.manager import DataSourceManager

router = APIRouter()


@router.get("/overview")
async def get_market_overview(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """获取市场概览数据"""
    try:
        # 使用数据源管理器获取市场概览
        manager = DataSourceManager()
        overview_data = await manager.get_market_overview()

        return {
            "success": True,
            "data": overview_data,
            "timestamp": "2025-10-18T20:00:00Z"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取市场概览失败: {str(e)}"
        )


@router.get("/sectors")
async def get_sector_performance(
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """获取板块表现数据"""
    try:
        manager = DataSourceManager()
        sectors_data = await manager.get_sector_performance(limit)

        return {
            "success": True,
            "data": sectors_data,
            "count": len(sectors_data),
            "timestamp": "2025-10-18T20:00:00Z"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取板块数据失败: {str(e)}"
        )


@router.get("/sectors/{sector_name}/stocks")
async def get_stocks_by_sector(
    sector_name: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """获取指定板块的股票列表"""
    try:
        manager = DataSourceManager()
        stocks_data = await manager.get_stocks_by_sector(sector_name, limit)

        return {
            "success": True,
            "sector": sector_name,
            "data": stocks_data,
            "count": len(stocks_data),
            "timestamp": "2025-10-18T20:00:00Z"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取板块股票失败: {str(e)}"
        )


@router.get("/index/{index_code}")
async def get_index_data(
    index_code: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """获取指数数据"""
    try:
        # 支持主要指数
        valid_indices = {
            "000001": "上证指数",
            "399001": "深证成指",
            "399006": "创业板指",
            "000688": "科创50"
        }

        if index_code not in valid_indices:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的指数代码: {index_code}"
            )

        manager = DataSourceManager()
        index_data = await manager.get_index_data(index_code)

        return {
            "success": True,
            "index_code": index_code,
            "index_name": valid_indices[index_code],
            "data": index_data,
            "timestamp": "2025-10-18T20:00:00Z"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取指数数据失败: {str(e)}"
        )


@router.get("/heatmap")
async def get_market_heatmap(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """获取市场热力图数据"""
    try:
        manager = DataSourceManager()
        heatmap_data = await manager.get_market_heatmap()

        return {
            "success": True,
            "data": heatmap_data,
            "timestamp": "2025-10-18T20:00:00Z"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取热力图数据失败: {str(e)}"
        )


@router.get("/northbound")
async def get_northbound_funds(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """获取北向资金数据"""
    try:
        manager = DataSourceManager()
        northbound_data = await manager.get_northbound_funds()

        return {
            "success": True,
            "data": northbound_data,
            "timestamp": "2025-10-18T20:00:00Z"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取北向资金数据失败: {str(e)}"
        )