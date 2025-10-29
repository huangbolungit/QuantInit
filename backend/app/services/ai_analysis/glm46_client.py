#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GLM-4.6 AI分析客户端
"""

import httpx
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

from app.core.config import settings


class GLM46Analyzer:
    """GLM-4.6 AI分析器"""

    def __init__(self):
        self.api_url = settings.GLM46_API_URL
        self.api_key = settings.ANTHROPIC_AUTH_TOKEN
        self.timeout = 30

    async def analyze_news_sentiment(self, news_text: str, stock_codes: List[str] = None) -> Dict[str, Any]:
        """分析新闻情感"""
        try:
            if not self.api_key or self.api_key == "your_glm46_api_key_here":
                return self._mock_sentiment_analysis(news_text, stock_codes)

            prompt = f"""
            请分析以下新闻的情感倾向和对相关股票的影响：

            新闻内容：
            {news_text}

            相关股票：{stock_codes if stock_codes else '无'}

            请按以下JSON格式返回结果：
            {{
                "overall_sentiment": "positive/negative/neutral",
                "sentiment_score": 0.0-1.0,
                "market_impact": "high/medium/low",
                "affected_stocks": [
                    {{
                        "stock_code": "股票代码",
                        "impact_score": 0.0-1.0,
                        "impact_type": "positive/negative/neutral"
                    }}
                ],
                "key_points": ["关键观点1", "关键观点2"],
                "confidence": 0.0-1.0
            }}
            """

            result = await self._call_api(prompt)
            return self._parse_json_response(result)

        except Exception as e:
            print(f"AI分析失败: {e}")
            return self._mock_sentiment_analysis(news_text, stock_codes)

    async def generate_market_summary(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成市场摘要"""
        try:
            if not self.api_key or self.api_key == "your_glm46_api_key_here":
                return self._mock_market_summary(market_data)

            prompt = f"""
            请基于以下市场数据生成一份简洁的市场分析摘要：

            {json.dumps(market_data, ensure_ascii=False, indent=2)}

            请按以下JSON格式返回结果：
            {{
                "market_trend": "bullish/bearish/neutral",
                "trend_strength": 0.0-1.0,
                "key_factors": ["关键因素1", "关键因素2"],
                "sector_performance": {{
                    "科技": "strong/moderate/weak",
                    "金融": "strong/moderate/weak",
                    "消费": "strong/moderate/weak"
                }},
                "risk_level": "high/medium/low",
                "investment_advice": "具体投资建议",
                "outlook": "市场展望"
            }}
            """

            result = await self._call_api(prompt)
            return self._parse_json_response(result)

        except Exception as e:
            print(f"生成市场摘要失败: {e}")
            return self._mock_market_summary(market_data)

    async def analyze_stock_factor(self, stock_code: str, factor_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析股票因子"""
        try:
            if not self.api_key or self.api_key == "your_glm46_api_key_here":
                return self._mock_factor_analysis(stock_code, factor_data)

            prompt = f"""
            请分析股票{stock_code}的多因子评分数据：

            {json.dumps(factor_data, ensure_ascii=False, indent=2)}

            请按以下JSON格式返回结果：
            {{
                "overall_assessment": "股票综合评价",
                "strengths": ["优势1", "优势2"],
                "weaknesses": ["劣势1", "劣势2"],
                "improvement_suggestions": ["建议1", "建议2"],
                "investment_holding_period": "short/medium/long",
                "confidence": 0.0-1.0
            }}
            """

            result = await self._call_api(prompt)
            return self._parse_json_response(result)

        except Exception as e:
            print(f"因子分析失败: {e}")
            return self._mock_factor_analysis(stock_code, factor_data)

    async def _call_api(self, prompt: str) -> str:
        """调用GLM-4.6 API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "glm-4.6",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.3
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()

            if "content" in result.get("choices", [{}])[0].get("message", {}):
                return result["choices"][0]["message"]["content"]
            else:
                raise ValueError("API响应格式错误")

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """解析JSON响应"""
        try:
            # 尝试直接解析JSON
            return json.loads(response_text)
        except:
            # 如果直接解析失败，尝试提取JSON部分
            try:
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start != -1 and end != 0:
                    json_str = response_text[start:end]
                    return json.loads(json_str)
            except:
                pass

            # 如果都失败了，返回错误信息
            return {
                "error": "Failed to parse AI response",
                "raw_response": response_text[:500]  # 只返回前500个字符
            }

    def _mock_sentiment_analysis(self, news_text: str, stock_codes: List[str] = None) -> Dict[str, Any]:
        """模拟情感分析"""
        import random

        sentiments = ["positive", "negative", "neutral"]
        sentiment = random.choice(sentiments)

        result = {
            "overall_sentiment": sentiment,
            "sentiment_score": random.uniform(0.3, 0.9),
            "market_impact": random.choice(["high", "medium", "low"]),
            "affected_stocks": [],
            "key_points": ["AI分析功能待实现", "需要配置GLM-4.6 API密钥"],
            "confidence": random.uniform(0.6, 0.8),
            "mock": True
        }

        if stock_codes:
            for code in stock_codes[:3]:  # 最多处理3只股票
                result["affected_stocks"].append({
                    "stock_code": code,
                    "impact_score": random.uniform(0.2, 0.8),
                    "impact_type": random.choice(["positive", "negative", "neutral"])
                })

        return result

    def _mock_market_summary(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """模拟市场摘要"""
        return {
            "market_trend": "neutral",
            "trend_strength": 0.5,
            "key_factors": ["AI分析功能待实现", "需要配置GLM-4.6 API密钥"],
            "sector_performance": {
                "科技": "moderate",
                "金融": "moderate",
                "消费": "moderate"
            },
            "risk_level": "medium",
            "investment_advice": "建议保持观望，等待AI分析功能完善",
            "outlook": "市场展望中性",
            "mock": True
        }

    def _mock_factor_analysis(self, stock_code: str, factor_data: Dict[str, Any]) -> Dict[str, Any]:
        """模拟因子分析"""
        return {
            "overall_assessment": f"股票{stock_code}需要更详细的因子分析",
            "strengths": ["因子分析框架已建立"],
            "weaknesses": ["需要真实数据支持", "AI分析功能待完善"],
            "improvement_suggestions": ["配置GLM-4.6 API密钥", "完善数据获取逻辑"],
            "investment_holding_period": "medium",
            "confidence": 0.5,
            "mock": True
        }

    def is_configured(self) -> bool:
        """检查是否已配置API密钥"""
        return bool(self.api_key and self.api_key != "your_glm46_api_key_here")