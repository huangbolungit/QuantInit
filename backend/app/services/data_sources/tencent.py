#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腾讯财经数据源客户端
"""

import httpx
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime

from app.core.config import settings


class TencentClient:
    """腾讯财经API客户端"""

    def __init__(self):
        self.base_url = settings.TENCENT_API_BASE_URL
        self.timeout = settings.REQUEST_TIMEOUT

    async def get_stock_quote(self, stock_code: str) -> Dict[str, Any]:
        """获取股票实时行情"""
        try:
            # 腾讯API格式：v_sh000001=行情数据
            symbol = self._convert_to_tencent_format(stock_code)
            url = f"{self.base_url}/q={symbol}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()

                # 解析腾讯返回的数据格式
                data = response.text
                if data and "=" in data:
                    quote_data = data.split("=")[1].strip('" ~')
                    fields = quote_data.split("~")

                    if len(fields) > 30:
                        return {
                            "stock_code": stock_code,
                            "name": fields[1],
                            "price": float(fields[3]) if fields[3] else 0.0,
                            "change": float(fields[31]) if fields[31] else 0.0,
                            "change_percent": float(fields[32]) if fields[32] else 0.0,
                            "volume": int(fields[6]) if fields[6] else 0,
                            "turnover": float(fields[37]) if fields[37] else 0.0,
                            "high": float(fields[41]) if fields[41] else 0.0,
                            "low": float(fields[42]) if fields[42] else 0.0,
                            "open": float(fields[43]) if fields[43] else 0.0,
                            "timestamp": datetime.now().isoformat()
                        }

                return {"error": "Failed to parse data", "stock_code": stock_code}

        except Exception as e:
            return {"error": str(e), "stock_code": stock_code}

    async def get_market_overview(self) -> Dict[str, Any]:
        """获取市场概览"""
        try:
            # 获取主要指数数据
            indices = ["sh000001", "sz399001", "sz399006"]  # 上证指数、深证成指、创业板指
            tasks = [self.get_stock_quote(index) for index in indices]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            overview = {
                "indices": [],
                "timestamp": datetime.now().isoformat()
            }

            for i, result in enumerate(results):
                if not isinstance(result, Exception) and "error" not in result:
                    overview["indices"].append(result)

            return overview

        except Exception as e:
            return {"error": str(e), "indices": []}

    def _convert_to_tencent_format(self, stock_code: str) -> str:
        """转换为腾讯API格式"""
        # 沪市：sh + 代码，深市：sz + 代码
        if stock_code.startswith("6"):
            return f"sh{stock_code}"
        elif stock_code.startswith(("0", "3")):
            return f"sz{stock_code}"
        else:
            return stock_code

    async def close(self):
        """关闭客户端"""
        pass