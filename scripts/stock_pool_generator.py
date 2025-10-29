#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Stock Pool Generator - 股票池生成器
用于生成多样化的股票池用于策略测试
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
import random
import logging

logger = logging.getLogger(__name__)

class StockPoolGenerator:
    """股票池生成器"""

    def __init__(self, data_dir: str = "data/historical/stocks/complete_csi800/stocks"):
        self.data_dir = Path(data_dir)
        self.available_stocks = self._scan_available_stocks()

    def _scan_available_stocks(self) -> List[str]:
        """扫描可用的股票数据"""
        stocks = set()

        # 检查主目录和子年份目录
        search_dirs = [self.data_dir]

        # 添加年份子目录
        for year_dir in self.data_dir.glob("20*"):
            if year_dir.is_dir():
                search_dirs.append(year_dir)

        for search_dir in search_dirs:
            if search_dir.exists():
                for file_path in search_dir.glob("*.csv"):
                    stock_code = file_path.stem
                    # 排除非股票代码文件
                    if len(stock_code) == 6 and stock_code.isdigit():
                        stocks.add(stock_code)

        logger.info(f"发现 {len(stocks)} 只股票数据")
        return sorted(list(stocks))

    def generate_expanded_pool(self,
                             target_size: int = 150,
                             exclude_st: bool = True,
                             min_market_cap: int = 5000000000,
                             min_avg_volume: int = 1000000,
                             seed: int = 42) -> List[str]:
        """生成扩展股票池"""

        random.seed(seed)
        np.random.seed(seed)

        # 基础过滤
        filtered_stocks = self.available_stocks.copy()

        # 排除ST股票
        if exclude_st:
            filtered_stocks = [s for s in filtered_stocks if not s.startswith('ST')
                             and not 'ST' in s]
            logger.info(f"排除ST股票后剩余: {len(filtered_stocks)}")

        # 如果过滤后数量仍足够，随机选择
        if len(filtered_stocks) >= target_size:
            selected_stocks = random.sample(filtered_stocks, target_size)
        else:
            selected_stocks = filtered_stocks
            logger.warning(f"可用股票数量 ({len(filtered_stocks)}) 少于目标数量 ({target_size})")

        # 确保包含一些知名股票
        blue_chips = ['000001', '000002', '600036', '600519', '000858',
                     '600000', '000001', '002415', '300015', '002594']

        for stock in blue_chips:
            if stock in self.available_stocks and stock not in selected_stocks:
                if len(selected_stocks) < target_size:
                    selected_stocks.append(stock)
                else:
                    selected_stocks[0] = stock  # 替换第一个

        logger.info(f"最终选择股票池: {len(selected_stocks)} 只")
        return sorted(selected_stocks)

    def generate_sector_balanced_pool(self, target_size: int = 100) -> List[str]:
        """生成行业平衡的股票池"""

        # 简单的行业分类（基于股票代码前缀）
        sector_mapping = {
            '银行': ['600036', '000001', '601398', '601988', '002142'],
            '地产': ['000002', '600048', '000069', '600383', '001979'],
            '保险': ['601318', '601601', '601336', '002594'],
            '证券': ['000776', '600030', '000783', '600837', '002736'],
            '科技': ['000063', '002415', '300015', '300033', '002230'],
            '医药': ['000423', '600276', '002007', '300003', '000538'],
            '消费': ['000858', '600519', '002304', '000568', '600887'],
            '能源': ['600028', '601857', '600123', '000983', '002128']
        }

        selected_stocks = []
        stocks_per_sector = max(1, target_size // len(sector_mapping))

        for sector, stocks in sector_mapping.items():
            available_in_sector = [s for s in stocks if s in self.available_stocks]
            if available_in_sector:
                # 每个行业选择一定数量的股票
                sector_selection = available_in_sector[:min(stocks_per_sector, len(available_in_sector))]
                selected_stocks.extend(sector_selection)

        # 如果数量不够，随机补充
        if len(selected_stocks) < target_size:
            remaining_stocks = [s for s in self.available_stocks if s not in selected_stocks]
            additional_needed = target_size - len(selected_stocks)
            if remaining_stocks:
                selected_stocks.extend(random.sample(remaining_stocks,
                                                   min(additional_needed, len(remaining_stocks))))

        logger.info(f"行业平衡股票池: {len(selected_stocks)} 只")
        return sorted(selected_stocks[:target_size])

    def get_stock_pool_stats(self, stock_pool: List[str]) -> Dict[str, Any]:
        """获取股票池统计信息"""
        return {
            'total_stocks': len(stock_pool),
            'available_stocks': len(self.available_stocks),
            'selection_ratio': len(stock_pool) / len(self.available_stocks) if self.available_stocks else 0,
            'pool_composition': {
                'first_10': stock_pool[:10] if len(stock_pool) >= 10 else stock_pool,
                'last_10': stock_pool[-10:] if len(stock_pool) >= 10 else stock_pool
            }
        }

if __name__ == "__main__":
    # 测试股票池生成器
    generator = StockPoolGenerator()

    # 生成扩展股票池
    expanded_pool = generator.generate_expanded_pool(target_size=150)
    print(f"扩展股票池 ({len(expanded_pool)} 只): {expanded_pool[:10]}...")

    # 生成行业平衡股票池
    balanced_pool = generator.generate_sector_balanced_pool(target_size=100)
    print(f"行业平衡股票池 ({len(balanced_pool)} 只): {balanced_pool[:10]}...")

    # 统计信息
    stats = generator.get_stock_pool_stats(expanded_pool)
    print(f"股票池统计: {stats}")