#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据源管理器
"""

from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime

from .eastmoney import EastmoneyClient
from .tencent import TencentClient
from app.core.config import settings


class DataSourceManager:
    """数据源管理器"""

    def __init__(self):
        self.eastmoney_client = EastmoneyClient()
        self.tencent_client = TencentClient()
        self.primary_source = "eastmoney"  # 主数据源
        self.fallback_sources = ["tencent"]  # 备用数据源

    async def get_stock_quote(self, stock_code: str) -> Dict[str, Any]:
        """获取股票行情，支持故障转移"""
        sources = [
            ("eastmoney", self.eastmoney_client.get_stock_quote),
            ("tencent", self.tencent_client.get_stock_quote)
        ]

        # 优先使用主数据源
        for source_name, source_method in sources:
            try:
                result = await source_method(stock_code)
                if "error" not in result and result.get("price", 0) > 0:
                    result["data_source"] = source_name
                    return result
            except Exception as e:
                print(f"数据源 {source_name} 获取失败: {e}")
                continue

        # 所有数据源都失败
        return {
            "error": "All data sources failed",
            "stock_code": stock_code,
            "data_source": "none"
        }

    async def get_market_overview(self) -> Dict[str, Any]:
        """获取市场概览"""
        try:
            # 优先使用东方财富
            result = await self.eastmoney_client.get_market_overview()
            if "error" not in result:
                result["data_source"] = "eastmoney"
                return result
        except Exception as e:
            print(f"东方财富获取市场概览失败: {e}")

        try:
            # 备用：腾讯财经
            result = await self.tencent_client.get_market_overview()
            if "error" not in result:
                result["data_source"] = "tencent"
                return result
        except Exception as e:
            print(f"腾讯财经获取市场概览失败: {e}")

        return {
            "error": "All data sources failed for market overview",
            "data_source": "none"
        }

    async def get_stock_list(self, market: str = "all") -> List[Dict[str, Any]]:
        """获取股票列表"""
        try:
            # 目前主要使用东方财富
            result = await self.eastmoney_client.get_stock_list(market)
            if isinstance(result, list):
                return result
            return []
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return []

    async def get_sector_performance(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取板块表现"""
        try:
            result = await self.eastmoney_client.get_sector_performance(limit)
            return result if isinstance(result, list) else []
        except Exception as exc:
            print(f"获取板块数据失败: {exc}")
            return []

    async def get_stocks_by_sector(self, sector_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取板块内股票"""
        try:
            result = await self.eastmoney_client.get_stocks_by_sector(sector_name, limit)
            return result if isinstance(result, list) else []
        except Exception as exc:
            print(f"获取板块 {sector_name} 股票失败: {exc}")
            return []

    async def get_kline_data(
        self,
        stock_code: str,
        period: str = "1d",
        count: int = 100
    ) -> List[Dict[str, Any]]:
        """获取K线数据"""
        try:
            result = await self.eastmoney_client.get_kline_data(stock_code, period, count)
            if isinstance(result, list):
                return result
            return []
        except Exception as e:
            print(f"获取K线数据失败: {e}")
            return []

    async def get_index_data(self, index_code: str) -> Dict[str, Any]:
        """获取指数数据"""
        prefix = "1" if index_code.startswith(("000", "60")) else "0"
        secid = f"{prefix}.{index_code}"
        try:
            data = await self.eastmoney_client.get_index_data(secid)
            if not data:
                return {"code": index_code, "error": "index data unavailable"}
            data["code"] = index_code
            return data
        except Exception as exc:
            print(f"获取指数 {index_code} 数据失败: {exc}")
            return {"code": index_code, "error": str(exc)}

    async def get_market_heatmap(self) -> List[Dict[str, Any]]:
        """获取市场热力图"""
        try:
            result = await self.eastmoney_client.get_market_heatmap()
            return result if isinstance(result, list) else []
        except Exception as exc:
            print(f"获取市场热力图失败: {exc}")
            return []

    async def get_northbound_funds(self) -> Dict[str, Any]:
        """获取北向资金数据"""
        try:
            return await self.eastmoney_client.get_northbound_funds()
        except Exception as exc:
            print(f"获取北向资金信息失败: {exc}")
            return {"error": str(exc)}

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        results = {
            "eastmoney": False,
            "tencent": False,
            "timestamp": datetime.now().isoformat()
        }

        # 检查东方财富
        try:
            test_result = await self.eastmoney_client.get_stock_quote("000001")
            results["eastmoney"] = "error" not in test_result
        except:
            results["eastmoney"] = False

        # 检查腾讯财经
        try:
            test_result = await self.tencent_client.get_stock_quote("000001")
            results["tencent"] = "error" not in test_result
        except:
            results["tencent"] = False

        return results

    async def close(self):
        """关闭所有客户端"""
        await self.eastmoney_client.close()
        await self.tencent_client.close()
