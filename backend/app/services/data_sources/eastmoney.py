#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东方财富数据源客户端
"""

import httpx
from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime

from ...core.config import settings


class EastmoneyClient:
    """东方财富API客户端"""

    def __init__(self):
        self.base_url = settings.EASTMONEY_API_BASE_URL
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://quote.eastmoney.com/",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        }
        self.timeout = settings.REQUEST_TIMEOUT

    async def get_stock_quote(self, stock_code: str) -> Dict[str, Any]:
        """获取股票报价信息"""
        try:
            detail = await self.get_stock_detail(stock_code)
            if detail:
                return {
                    "stock_code": detail.get("code", stock_code),
                    "name": detail.get("name", ""),
                    "price": detail.get("current", 0),
                    "change": detail.get("change_amount", 0),
                    "change_pct": detail.get("change_pct", 0),
                    "volume": detail.get("volume", 0),
                    "turnover": detail.get("turnover", 0),
                    "turnover_rate": detail.get("turnover_rate", 0),
                    "pe_ratio": detail.get("pe_ratio", 0),
                    "pb_ratio": detail.get("pb_ratio", 0),
                    "market_cap": detail.get("market_cap", 0),
                    "circulating_market_cap": detail.get("circulating_market_cap", 0),
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as exc:  # pragma: no cover - fallback handled below
            print(f"东方财富股票行情API调用失败: {exc}")

        return self._get_mock_stock_quote(stock_code)

    async def get_stock_list(self, market: str = "all", limit: int = 1000) -> List[Dict[str, Any]]:
        """获取股票列表"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                market_map = {
                    "all": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23",
                    "sh": "m:1 t:2,m:1 t:23",
                    "sz": "m:0 t:6,m:0 t:80"
                }
                fs = market_map.get(market.lower(), market_map["all"])

                params = {
                    "pn": 1,
                    "pz": limit,
                    "po": 1,
                    "np": 1,
                    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                    "fltt": 2,
                    "invt": 2,
                    "fid": "f3",
                    "fs": fs,
                    "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152"
                }

                response = await client.get(
                    f"{self.base_url}/api/qt/clist/get",
                    params=params,
                    headers=self.headers
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_stock_list_data(data)
        except Exception as exc:  # pragma: no cover - fallback handled below
            print(f"东方财富股票列表API调用失败: {exc}")

        return self._get_mock_stock_list()

    async def get_market_overview(self) -> Dict[str, Any]:
        """获取市场概览数据"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 获取主要指数数据
                index_codes = "1.000001,0.399001,0.399006,0.000688"  # 上证、深成、创业板、科创50
                params = {
                    "fields": "f43,f44,f45,f46,f47,f48,f49,f50,f51,f52",
                    "secids": index_codes
                }

                response = await client.get(
                    f"{self.base_url}/api/qt/stock/get",
                    params=params,
                    headers=self.headers
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_market_overview(data)
                else:
                    return self._get_mock_market_overview()

        except Exception as e:
            print(f"东方财富市场概览API调用失败: {e}")
            return self._get_mock_market_overview()

    async def get_sector_performance(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取板块表现数据"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {
                    "pn": 1,
                    "pz": limit,
                    "po": 1,
                    "np": 1,
                    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                    "fltt": 2,
                    "invt": 2,
                    "fid": "f3",
                    "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23",  # 主要行业板块
                    "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152"
                }

                response = await client.get(
                    f"{self.base_url}/api/qt/clist/get",
                    params=params,
                    headers=self.headers
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_sector_data(data)
                else:
                    return self._get_mock_sector_data()

        except Exception as e:
            print(f"东方财富板块API调用失败: {e}")
            return self._get_mock_sector_data()

    async def get_stocks_by_sector(self, sector_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取指定板块的股票列表"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 这里需要根据板块名称获取板块代码，简化处理
                params = {
                    "pn": 1,
                    "pz": limit,
                    "po": 1,
                    "np": 1,
                    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                    "fltt": 2,
                    "invt": 2,
                    "fid": "f3",
                    "fs": f"m:0 t:6 m:1 t:2",  # 这里需要动态获取板块代码
                    "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152"
                }

                response = await client.get(
                    f"{self.base_url}/api/qt/clist/get",
                    params=params,
                    headers=self.headers
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_stock_list_data(data)
                else:
                    return self._get_mock_stock_data(sector_name)

        except Exception as e:
            print(f"东方财富股票列表API调用失败: {e}")
            return self._get_mock_stock_data(sector_name)

    async def get_index_data(self, index_code: str) -> Dict[str, Any]:
        """获取指数数据"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {
                    "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f14,f15,f16,f17,f18",
                    "secids": index_code
                }
                response = await client.get(
                    f"{self.base_url}/api/qt/stock/get",
                    params=params,
                    headers=self.headers
                )
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_index_data(data)
        except Exception as exc:  # pragma: no cover - fallback handled below
            print(f"东方财富指数API调用失败: {exc}")

        return self._get_mock_index_data(index_code)

    async def get_stock_detail(self, stock_code: str) -> Dict[str, Any]:
        """获取股票详细信息"""
        try:
            # 格式化股票代码
            if stock_code.startswith("6"):
                secid = f"1.{stock_code}"  # 上海
            else:
                secid = f"0.{stock_code}"  # 深圳

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {
                    "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152",
                    "secids": secid
                }

                response = await client.get(
                    f"{self.base_url}/api/qt/stock/get",
                    params=params,
                    headers=self.headers
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_stock_detail(data)
                else:
                    return self._get_mock_stock_detail(stock_code)

        except Exception as e:
            print(f"东方财富股票详情API调用失败: {e}")
            return self._get_mock_stock_detail(stock_code)

    async def get_market_heatmap(self) -> List[Dict[str, Any]]:
        """获取市场热力图数据"""
        try:
            sectors = await self.get_sector_performance(limit=60)
            if sectors:
                return [
                    {
                        "code": sector["code"],
                        "name": sector["name"],
                        "change_pct": sector["change_pct"],
                        "turnover": sector.get("volume", 0)
                    }
                    for sector in sectors
                ]
        except Exception as exc:  # pragma: no cover - fallback handled below
            print(f"东方财富热力图数据获取失败: {exc}")

        return self._get_mock_heatmap()

    async def get_northbound_funds(self) -> Dict[str, Any]:
        """获取北向资金数据"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {
                    "fields": "f1,f2,f3,f4,f5,f6",
                    "lmt": 0
                }
                response = await client.get(
                    f"{self.base_url}/api/qt/kamt/get",
                    params=params,
                    headers=self.headers
                )
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_northbound_data(data)
        except Exception as exc:  # pragma: no cover - fallback handled below
            print(f"东方财富北向资金API调用失败: {exc}")

        return self._get_mock_northbound_funds()

    async def close(self):
        """关闭客户端（目前为占位方法，预留资源清理接口）"""
        return

    async def get_kline_data(self, stock_code: str, period: str = "daily") -> List[Dict[str, Any]]:
        """获取K线数据"""
        try:
            # 格式化股票代码
            if stock_code.startswith("6"):
                secid = f"1.{stock_code}"  # 上海
            else:
                secid = f"0.{stock_code}"  # 深圳

            # 根据周期设置参数
            period_map = {
                "daily": "101",
                "weekly": "102",
                "monthly": "103"
            }
            klt = period_map.get(period, "101")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {
                    "fields1": "f1,f2,f3,f4,f5,f6",
                    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                    "secid": secid,
                    "klt": klt,
                    "fqt": 1,  # 前复权
                    "beg": "0",
                    "end": "20500000"
                }

                response = await client.get(
                    f"{self.base_url}/api/qt/stock/kline/get",
                    params=params,
                    headers=self.headers
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_kline_data(data)
                else:
                    return self._get_mock_kline_data(stock_code)

        except Exception as e:
            print(f"东方财富K线数据API调用失败: {e}")
            return self._get_mock_kline_data(stock_code)

    def _parse_market_overview(self, data: Dict) -> Dict[str, Any]:
        """解析市场概览数据"""
        if not data.get("data"):
            return self._get_mock_market_overview()

        result = {}
        for item in data["data"]["diff"]:
            name = item.get("f58", "")
            change_pct = item.get("f3", 0)
            current = item.get("f2", 0)
            volume = item.get("f5", 0)

            result[name] = {
                "name": name,
                "current": current,
                "change_pct": change_pct,
                "volume": volume
            }

        return result

    def _parse_sector_data(self, data: Dict) -> List[Dict[str, Any]]:
        """解析板块数据"""
        if not data.get("data"):
            return self._get_mock_sector_data()

        sectors = []
        for item in data["data"]["diff"]:
            sector = {
                "name": item.get("f14", ""),
                "code": item.get("f12", ""),
                "change_pct": item.get("f3", 0),
                "current": item.get("f2", 0),
                "volume": item.get("f5", 0),
                "leader_stock": item.get("f14", "")  # 领涨股
            }
            sectors.append(sector)

        return sectors[:20]  # 返回前20个板块

    def _parse_stock_list_data(self, data: Dict) -> List[Dict[str, Any]]:
        """解析股票列表数据"""
        if not data.get("data"):
            return []

        stocks = []
        for item in data["data"]["diff"]:
            stock = {
                "code": item.get("f12", ""),
                "name": item.get("f14", ""),
                "current": item.get("f2", 0),
                "change_pct": item.get("f3", 0),
                "change_amount": item.get("f4", 0),
                "volume": item.get("f5", 0),
                "turnover_rate": item.get("f8", 0),
                "pe_ratio": item.get("f9", 0),
                "market_cap": item.get("f20", 0)
            }
            stocks.append(stock)

        return stocks

    def _parse_index_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """解析指数数据"""
        if not data.get("data"):
            return {}

        item = data["data"]["diff"][0] if data["data"]["diff"] else {}
        return {
            "code": item.get("f12", ""),
            "name": item.get("f14", ""),
            "current": item.get("f2", 0),
            "change_pct": item.get("f3", 0),
            "change_amount": item.get("f4", 0),
            "open": item.get("f17", 0),
            "high": item.get("f15", 0),
            "low": item.get("f16", 0),
            "volume": item.get("f5", 0),
            "turnover": item.get("f6", 0),
            "timestamp": datetime.now().isoformat()
        }

    def _parse_stock_detail(self, data: Dict) -> Dict[str, Any]:
        """解析股票详情数据"""
        if not data.get("data"):
            return {}

        item = data["data"]["diff"][0] if data["data"]["diff"] else {}
        return {
            "code": item.get("f12", ""),
            "name": item.get("f14", ""),
            "current": item.get("f2", 0),
            "change_pct": item.get("f3", 0),
            "change_amount": item.get("f4", 0),
            "open": item.get("f17", 0),
            "high": item.get("f15", 0),
            "low": item.get("f16", 0),
            "volume": item.get("f5", 0),
            "turnover": item.get("f6", 0),
            "turnover_rate": item.get("f8", 0),
            "pe_ratio": item.get("f9", 0),
            "pb_ratio": item.get("f23", 0),
            "market_cap": item.get("f20", 0),
            "circulating_market_cap": item.get("f21", 0)
        }

    def _parse_kline_data(self, data: Dict) -> List[Dict[str, Any]]:
        """解析K线数据"""
        if not data.get("data"):
            return []

        klines = []
        for item in data["data"]["klines"]:
            parts = item.split(",")
            kline = {
                "date": parts[0],
                "open": float(parts[1]),
                "close": float(parts[2]),
                "high": float(parts[3]),
                "low": float(parts[4]),
                "volume": int(parts[5]),
                "turnover": float(parts[6])
            }
            klines.append(kline)

        return klines

    # Mock数据方法 (用于开发和测试)
    def _get_mock_market_overview(self) -> Dict[str, Any]:
        """获取模拟市场概览数据"""
        return {
            "上证指数": {"name": "上证指数", "current": 3087.53, "change_pct": -0.28, "volume": 2850000000},
            "深证成指": {"name": "深证成指", "current": 9876.32, "change_pct": 0.45, "volume": 3520000000},
            "创业板指": {"name": "创业板指", "current": 1923.45, "change_pct": 1.23, "volume": 1560000000},
            "科创50": {"name": "科创50", "current": 876.54, "change_pct": -0.67, "volume": 780000000}
        }

    def _get_mock_sector_data(self) -> List[Dict[str, Any]]:
        """获取模拟板块数据"""
        return [
            {"name": "半导体", "code": "BK0475", "change_pct": 3.45, "current": 1256.78, "volume": 1560000000, "leader_stock": "中芯国际"},
            {"name": "新能源", "code": "BK0476", "change_pct": 2.67, "current": 2345.67, "volume": 2340000000, "leader_stock": "比亚迪"},
            {"name": "医药生物", "code": "BK0477", "change_pct": 1.89, "current": 3456.78, "volume": 1870000000, "leader_stock": "恒瑞医药"},
            {"name": "电子信息", "code": "BK0478", "change_pct": 1.56, "current": 2876.54, "volume": 1650000000, "leader_stock": "京东方A"}
        ]

    def _get_mock_stock_data(self, sector_name: str) -> List[Dict[str, Any]]:
        """获取模拟股票数据"""
        return [
            {"code": "000001", "name": "平安银行", "current": 12.85, "change_pct": 1.23, "volume": 45000000, "turnover_rate": 0.67},
            {"code": "000002", "name": "万科A", "current": 15.67, "change_pct": -0.45, "volume": 32000000, "turnover_rate": 0.34},
            {"code": "000858", "name": "五粮液", "current": 178.90, "change_pct": 2.34, "volume": 12000000, "turnover_rate": 0.23}
        ]

    def _get_mock_stock_list(self) -> List[Dict[str, Any]]:
        """获取模拟股票列表"""
        return [
            {"code": "000001", "name": "平安银行", "current": 12.85, "change_pct": 1.23, "volume": 45000000, "turnover_rate": 0.67, "pe_ratio": 8.5, "market_cap": 35600000000},
            {"code": "600519", "name": "贵州茅台", "current": 1789.0, "change_pct": -0.85, "volume": 1200000, "turnover_rate": 0.12, "pe_ratio": 32.5, "market_cap": 2245000000000},
            {"code": "300750", "name": "宁德时代", "current": 195.3, "change_pct": 0.65, "volume": 15400000, "turnover_rate": 0.95, "pe_ratio": 28.1, "market_cap": 890000000000}
        ]

    def _get_mock_stock_detail(self, stock_code: str) -> Dict[str, Any]:
        """获取模拟股票详情"""
        return {
            "code": stock_code,
            "name": f"股票{stock_code}",
            "current": 25.67,
            "change_pct": 1.45,
            "change_amount": 0.37,
            "open": 25.30,
            "high": 26.00,
            "low": 25.10,
            "volume": 28000000,
            "turnover": 712000000,
            "turnover_rate": 1.23,
            "pe_ratio": 18.5,
            "pb_ratio": 2.1,
            "market_cap": 28700000000,
            "circulating_market_cap": 24500000000
        }

    def _get_mock_kline_data(self, stock_code: str) -> List[Dict[str, Any]]:
        """获取模拟K线数据"""
        import random
        from datetime import datetime, timedelta

        klines = []
        base_price = 25.0
        for i in range(30):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            change = random.uniform(-2, 2)
            open_price = base_price + random.uniform(-1, 1)
            close_price = open_price + change
            high_price = max(open_price, close_price) + random.uniform(0, 1)
            low_price = min(open_price, close_price) - random.uniform(0, 1)
            volume = random.randint(10000000, 50000000)

            klines.append({
                "date": date,
                "open": round(open_price, 2),
                "close": round(close_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "volume": volume,
                "turnover": round(volume * close_price, 0)
            })
            base_price = close_price

        return list(reversed(klines))

    def _get_mock_stock_quote(self, stock_code: str) -> Dict[str, Any]:
        """获取模拟股票行情"""
        detail = self._get_mock_stock_detail(stock_code)
        return {
            "stock_code": detail["code"],
            "name": detail["name"],
            "price": detail["current"],
            "change": detail["change_amount"],
            "change_pct": detail["change_pct"],
            "volume": detail["volume"],
            "turnover": detail["turnover"],
            "turnover_rate": detail["turnover_rate"],
            "pe_ratio": detail["pe_ratio"],
            "pb_ratio": detail["pb_ratio"],
            "market_cap": detail["market_cap"],
            "circulating_market_cap": detail["circulating_market_cap"],
            "timestamp": datetime.now().isoformat(),
            "mock": True
        }

    def _get_mock_index_data(self, index_code: str) -> Dict[str, Any]:
        """获取模拟指数数据"""
        mock_indices = {
            "1.000001": {"name": "上证指数", "current": 3087.53, "change_pct": -0.28, "change_amount": -8.72},
            "0.399001": {"name": "深证成指", "current": 9876.32, "change_pct": 0.45, "change_amount": 44.50},
            "0.399006": {"name": "创业板指", "current": 1923.45, "change_pct": 1.23, "change_amount": 23.40},
            "0.000688": {"name": "科创50", "current": 876.54, "change_pct": -0.67, "change_amount": -5.90}
        }
        data = mock_indices.get(index_code, {"name": "指数", "current": 0, "change_pct": 0, "change_amount": 0})
        return {
            "code": index_code,
            **data,
            "timestamp": datetime.now().isoformat(),
            "mock": True
        }

    def _get_mock_heatmap(self) -> List[Dict[str, Any]]:
        """获取模拟热力图数据"""
        return [
            {"code": "BK0475", "name": "半导体", "change_pct": 3.45, "turnover": 1560000000},
            {"code": "BK0476", "name": "新能源", "change_pct": 2.67, "turnover": 2340000000},
            {"code": "BK0477", "name": "医药生物", "change_pct": 1.89, "turnover": 1870000000},
            {"code": "BK0478", "name": "电子信息", "change_pct": 1.56, "turnover": 1650000000},
            {"code": "BK0480", "name": "金融", "change_pct": -0.85, "turnover": 980000000}
        ]

    def _parse_northbound_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """解析北向资金数据"""
        if not data.get("data"):
            return {}

        result = data["data"]
        return {
            "northbound": result.get("hk2sh", {}).get("netBuy", 0),
            "northbound_sh": result.get("hk2sh", {}).get("netBuy", 0),
            "northbound_sz": result.get("hk2sz", {}).get("netBuy", 0),
            "southbound": result.get("sh2hk", {}).get("netBuy", 0),
            "timestamp": datetime.now().isoformat()
        }

    def _get_mock_northbound_funds(self) -> Dict[str, Any]:
        """获取模拟北向资金数据"""
        return {
            "northbound": 1250000000,
            "northbound_sh": 720000000,
            "northbound_sz": 530000000,
            "southbound": -320000000,
            "timestamp": datetime.now().isoformat(),
            "mock": True
        }
