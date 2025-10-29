#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多因子评分引擎
"""

from typing import Dict, List, Any, Optional
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, date

from ...core.config import settings
from ..factors.momentum import MomentumFactor
from ..factors.sentiment import SentimentFactor
from ..factors.value import ValueFactor
from ..factors.quality import QualityFactor


class ScoringEngine:
    """多因子评分引擎"""

    def __init__(self):
        self.weights = settings.factor_weights
        self.entry_threshold = settings.POOL_ENTRY_THRESHOLD
        self.exit_threshold = settings.POOL_EXIT_THRESHOLD
        self.max_pool_size = settings.MAX_POOL_SIZE

        # 初始化因子计算器
        self.momentum_factor = MomentumFactor()
        self.sentiment_factor = SentimentFactor()
        self.value_factor = ValueFactor()
        self.quality_factor = QualityFactor()

    async def calculate_composite_score(
        self,
        stock_code: str,
        market_data: Dict[str, Any],
        news_data: Optional[List[Dict]] = None
    ) -> Dict[str, float]:
        """
        计算股票的综合评分

        Args:
            stock_code: 股票代码
            market_data: 市场数据
            news_data: 新闻数据（可选）

        Returns:
            包含各因子得分和综合得分的字典
        """
        try:
            # 1. 计算各因子得分
            momentum_score = await self.momentum_factor.calculate(stock_code, market_data)
            sentiment_score = await self.sentiment_factor.calculate(stock_code, market_data, news_data)
            value_score = await self.value_factor.calculate(stock_code, market_data)
            quality_score = await self.quality_factor.calculate(stock_code, market_data)

            # 2. 归一化处理 (0-100分)
            normalized_scores = self._normalize_factors({
                'momentum': momentum_score,
                'sentiment': sentiment_score,
                'value': value_score,
                'quality': quality_score
            })

            # 3. 加权求和
            composite_score = sum(
                normalized_scores[factor] * weight
                for factor, weight in self.weights.items()
            )

            # 4. 确保分数在0-100范围内
            composite_score = max(0, min(100, composite_score))

            return {
                'momentum_score': normalized_scores['momentum'],
                'sentiment_score': normalized_scores['sentiment'],
                'value_score': normalized_scores['value'],
                'quality_score': normalized_scores['quality'],
                'total_score': round(composite_score, 2),
                'calculated_at': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"计算股票 {stock_code} 评分失败: {e}")
            return {
                'momentum_score': 50.0,
                'sentiment_score': 50.0,
                'value_score': 50.0,
                'quality_score': 50.0,
                'total_score': 50.0,
                'calculated_at': datetime.now().isoformat(),
                'error': str(e)
            }

    async def batch_calculate_scores(
        self,
        stock_list: List[str],
        market_data_dict: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, float]]:
        """批量计算股票评分"""
        tasks = []
        for stock_code in stock_list:
            market_data = market_data_dict.get(stock_code, {})
            task = self.calculate_composite_score(stock_code, market_data)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 组装结果
        score_dict = {}
        for i, stock_code in enumerate(stock_list):
            if isinstance(results[i], Exception):
                print(f"股票 {stock_code} 评分计算异常: {results[i]}")
                continue
            score_dict[stock_code] = results[i]

        return score_dict

    def _normalize_factors(self, factor_scores: Dict[str, float]) -> Dict[str, float]:
        """
        因子归一化处理

        使用百分位排名的方法，将不同量纲的因子得分统一到0-100分范围
        """
        normalized = {}

        # 简单的线性归一化 (实际应用中可以使用历史数据计算百分位)
        for factor, score in factor_scores.items():
            if isinstance(score, (int, float)) and not np.isnan(score):
                # 根据因子特性决定归一化方向
                if factor in ['momentum', 'sentiment']:
                    # 动量和情绪因子：越高越好
                    normalized_score = min(100, max(0, score))
                else:
                    # 价值和质量因子：需要根据实际计算逻辑调整
                    normalized_score = min(100, max(0, score))
            else:
                normalized_score = 50.0  # 默认中性评分

            normalized[factor] = normalized_score

        return normalized

    def generate_pool_suggestions(
        self,
        current_scores: Dict[str, Dict[str, float]],
        previous_scores: Dict[str, Dict[str, float]],
        current_pool: List[str]
    ) -> List[Dict[str, Any]]:
        """
        生成股票池调仓建议

        Args:
            current_scores: 最新评分数据
            previous_scores: 上次评分数据
            current_pool: 当前股票池

        Returns:
            调仓建议列表
        """
        suggestions = []

        # 1. 检查入池建议
        for stock_code, score_data in current_scores.items():
            if stock_code in current_pool:
                continue  # 已在池中，跳过

            total_score = score_data.get('total_score', 0)
            prev_total = previous_scores.get(stock_code, {}).get('total_score', 0)

            # 入池条件：当前评分超过阈值且评分显著上升
            if (total_score >= self.entry_threshold and
                total_score - prev_total >= 5 and  # 评分上升至少5分
                len(current_pool) < self.max_pool_size):

                suggestion = {
                    'stock_code': stock_code,
                    'action': 'ADD',
                    'reason': self._generate_add_reason(score_data, prev_total),
                    'score': total_score,
                    'score_change': total_score - prev_total,
                    'key_factors': self._identify_key_factors(score_data, previous_scores.get(stock_code, {})),
                    'created_at': datetime.now().isoformat()
                }
                suggestions.append(suggestion)

        # 2. 检查出池建议
        for stock_code in current_pool:
            if stock_code not in current_scores:
                continue  # 没有评分数据，跳过

            score_data = current_scores[stock_code]
            total_score = score_data.get('total_score', 0)
            prev_total = previous_scores.get(stock_code, {}).get('total_score', total_score)

            # 出池条件：评分跌破阈值或显著下降
            if (total_score <= self.exit_threshold or
                total_score - prev_total <= -10):  # 评分下降至少10分

                suggestion = {
                    'stock_code': stock_code,
                    'action': 'REMOVE',
                    'reason': self._generate_remove_reason(score_data, prev_total),
                    'score': total_score,
                    'score_change': total_score - prev_total,
                    'key_factors': self._identify_key_factors(score_data, previous_scores.get(stock_code, {})),
                    'created_at': datetime.now().isoformat()
                }
                suggestions.append(suggestion)

        # 3. 按优先级排序建议
        suggestions.sort(key=lambda x: abs(x['score_change']), reverse=True)

        return suggestions

    def _generate_add_reason(self, score_data: Dict[str, float], prev_score: float) -> str:
        """生成入池建议理由"""
        reasons = []

        total_score = score_data.get('total_score', 0)
        momentum = score_data.get('momentum_score', 0)
        sentiment = score_data.get('sentiment_score', 0)
        value = score_data.get('value_score', 0)
        quality = score_data.get('quality_score', 0)

        if momentum >= 70:
            reasons.append("动量表现强劲")
        if sentiment >= 70:
            reasons.append("市场情绪积极")
        if value >= 70:
            reasons.append("估值具有吸引力")
        if quality >= 70:
            reasons.append("基本面质量优秀")

        if total_score >= 95:
            return f"综合评分{total_score}分，表现卓越，{', '.join(reasons[:2])}"
        else:
            return f"综合评分{total_score}分，评分上升{total_score - prev_score:.1f}分，{', '.join(reasons[:2])}"

    def _generate_remove_reason(self, score_data: Dict[str, float], prev_score: float) -> str:
        """生成出池建议理由"""
        reasons = []

        total_score = score_data.get('total_score', 0)
        momentum = score_data.get('momentum_score', 0)
        sentiment = score_data.get('sentiment_score', 0)
        value = score_data.get('value_score', 0)
        quality = score_data.get('quality_score', 0)

        if momentum <= 30:
            reasons.append("动量转弱")
        if sentiment <= 30:
            reasons.append("市场情绪恶化")
        if value <= 30:
            reasons.append("估值偏高")
        if quality <= 30:
            reasons.append("基本面出现风险")

        if total_score <= 70:
            return f"综合评分{total_score}分，表现不佳，{', '.join(reasons[:2])}"
        else:
            return f"综合评分下降{prev_score - total_score:.1f}分至{total_score}分，{', '.join(reasons[:2])}"

    def _identify_key_factors(
        self,
        current_scores: Dict[str, float],
        previous_scores: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """识别关键影响因子"""
        key_factors = []

        for factor in ['momentum_score', 'sentiment_score', 'value_score', 'quality_score']:
            current = current_scores.get(factor, 0)
            previous = previous_scores.get(factor, 0)
            change = current - previous

            if abs(change) >= 5:  # 变化超过5分认为是关键因子
                factor_names = {
                    'momentum_score': '动量因子',
                    'sentiment_score': '情绪因子',
                    'value_score': '价值因子',
                    'quality_score': '质量因子'
                }

                key_factors.append({
                    'factor': factor_names.get(factor, factor),
                    'current_score': current,
                    'previous_score': previous,
                    'change': round(change, 2),
                    'impact': 'positive' if change > 0 else 'negative'
                })

        # 按变化幅度排序
        key_factors.sort(key=lambda x: abs(x['change']), reverse=True)

        return key_factors[:3]  # 返回前3个关键因子

    def get_factor_explanation(self, factor_name: str, score: float) -> str:
        """获取因子评分解释"""
        explanations = {
            'momentum': {
                'high': '动量强劲，价格趋势向上，短期表现优异',
                'medium': '动量平稳，价格走势相对稳定',
                'low': '动量疲软，价格趋势向下，短期表现不佳'
            },
            'sentiment': {
                'high': '市场情绪积极，资金流入明显，新闻面利好',
                'medium': '市场情绪中性，资金流向相对平衡',
                'low': '市场情绪悲观，资金流出压力，新闻面偏空'
            },
            'value': {
                'high': '估值优势明显，具备较好的安全边际',
                'medium': '估值水平适中，符合行业平均水平',
                'low': '估值偏高，可能存在泡沫风险'
            },
            'quality': {
                'high': '基本面质量优秀，财务状况健康，盈利能力强',
                'medium': '基本面质量良好，财务状况相对稳定',
                'low': '基本面质量一般，需要关注财务风险'
            }
        }

        factor_key = factor_name.replace('_score', '')
        explanation_dict = explanations.get(factor_key, {})

        if score >= 70:
            return explanation_dict.get('high', '表现优秀')
        elif score >= 40:
            return explanation_dict.get('medium', '表现一般')
        else:
            return explanation_dict.get('low', '需要关注')