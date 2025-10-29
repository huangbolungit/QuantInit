#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Advanced Factor Hunt Engine - 高级因子搜索引擎
系统性测试多种类型的量化因子，寻找真正有效的策略
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from pathlib import Path
import logging
from typing import Dict, List, Any, Tuple
import warnings
warnings.filterwarnings('ignore')

# 添加项目路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.bias_free_backtest_engine import (
    BiasFreeBacktestEngine,
    SignalGenerator,
    TradingInstruction,
    DataSnapshot
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MomentumSignalGenerator(SignalGenerator):
    """动量因子信号生成器 - 多周期动量策略"""

    def __init__(self, lookback_period: int = 20, momentum_threshold: float = 0.05):
        super().__init__(f"Momentum_{lookback_period}days_{momentum_threshold}")
        self.lookback_period = lookback_period
        self.momentum_threshold = momentum_threshold

    def generate_signals(self, snapshot: DataSnapshot) -> List[TradingInstruction]:
        instructions = []

        for stock_code, factors in snapshot.factor_data.items():
            if 'momentum_score' in factors and not pd.isna(factors['momentum_score']):
                momentum = factors['momentum_score']

                # 正向动量：买入上涨股票
                if momentum > self.momentum_threshold:
                    instructions.append(TradingInstruction(
                        stock_code=stock_code,
                        action='BUY',
                        quantity=1000,
                        reason=f"Momentum: {momentum:.4f} > {self.momentum_threshold}",
                        timestamp=snapshot.date
                    ))

        return instructions

    @staticmethod
    def calculate_momentum(data: pd.DataFrame, lookback_period: int = 20) -> float:
        """计算动量因子：过去N天的收益率"""
        if len(data) < lookback_period + 1:
            return np.nan

        start_price = data['close'].iloc[-(lookback_period + 1)]
        end_price = data['close'].iloc[-1]

        momentum = (end_price - start_price) / start_price
        return momentum

class MeanReversionSignalGenerator(SignalGenerator):
    """均值回归因子信号生成器 - 基于移动均值的回归策略"""

    def __init__(self, lookback_period: int = 20, deviation_threshold: float = 2.0):
        super().__init__(f"MeanReversion_{lookback_period}days_{deviation_threshold}std")
        self.lookback_period = lookback_period
        self.deviation_threshold = deviation_threshold

    def generate_signals(self, snapshot: DataSnapshot) -> List[TradingInstruction]:
        instructions = []

        for stock_code, factors in snapshot.factor_data.items():
            if 'mean_reversion_score' in factors and not pd.isna(factors['mean_reversion_score']):
                reversion_score = factors['mean_reversion_score']

                # 价格低于均值过多时买入（均值回归）
                if reversion_score < -self.deviation_threshold:
                    instructions.append(TradingInstruction(
                        stock_code=stock_code,
                        action='BUY',
                        quantity=1000,
                        reason=f"Mean Reversion: {reversion_score:.4f} < -{self.deviation_threshold}",
                        timestamp=snapshot.date
                    ))

        return instructions

    @staticmethod
    def calculate_mean_reversion(data: pd.DataFrame, lookback_period: int = 20) -> float:
        """计算均值回归因子：当前价格相对于移动均值的偏离度"""
        if len(data) < lookback_period:
            return np.nan

        recent_prices = data['close'].iloc[-lookback_period:]
        current_price = data['close'].iloc[-1]

        mean_price = recent_prices.mean()
        std_price = recent_prices.std()

        if std_price > 0:
            z_score = (current_price - mean_price) / std_price
            return z_score

        return 0.0

class VolatilitySignalGenerator(SignalGenerator):
    """波动率因子信号生成器 - 低波动率偏向策略"""

    def __init__(self, lookback_period: int = 20, volatility_percentile: float = 0.3):
        super().__init__(f"LowVolatility_{lookback_period}days_{volatility_percentile}")
        self.lookback_period = lookback_period
        self.volatility_percentile = volatility_percentile

    def generate_signals(self, snapshot: DataSnapshot) -> List[TradingInstruction]:
        instructions = []

        for stock_code, factors in snapshot.factor_data.items():
            if 'volatility_rank' in factors and not pd.isna(factors['volatility_rank']):
                vol_rank = factors['volatility_rank']

                # 买入波动率最低的股票（低波动率异常）
                if vol_rank <= self.volatility_percentile:
                    instructions.append(TradingInstruction(
                        stock_code=stock_code,
                        action='BUY',
                        quantity=1000,
                        reason=f"Low Volatility: rank {vol_rank:.4f} <= {self.volatility_percentile}",
                        timestamp=snapshot.date
                    ))

        return instructions

    @staticmethod
    def calculate_volatility(data: pd.DataFrame, lookback_period: int = 20) -> float:
        """计算波动率因子：过去N天收益率的标准差"""
        if len(data) < lookback_period:
            return np.nan

        returns = data['close'].pct_change().iloc[-lookback_period:].dropna()
        if len(returns) > 0:
            return returns.std() * np.sqrt(252)  # 年化波动率

        return np.nan

class LiquiditySignalGenerator(SignalGenerator):
    """流动性因子信号生成器 - 基于成交量的流动性策略"""

    def __init__(self, lookback_period: int = 20, liquidity_threshold: float = 0.5):
        super().__init__(f"Liquidity_{lookback_period}days_{liquidity_threshold}")
        self.lookback_period = lookback_period
        self.liquidity_threshold = liquidity_threshold

    def generate_signals(self, snapshot: DataSnapshot) -> List[TradingInstruction]:
        instructions = []

        for stock_code, factors in snapshot.factor_data.items():
            if 'liquidity_score' in factors and not pd.isna(factors['liquidity_score']):
                liquidity = factors['liquidity_score']

                # 买入流动性适中的股票（避免流动性过高或过低）
                if self.liquidity_threshold <= liquidity <= 2.0:
                    instructions.append(TradingInstruction(
                        stock_code=stock_code,
                        action='BUY',
                        quantity=1000,
                        reason=f"Liquidity: {liquidity:.4f} in optimal range",
                        timestamp=snapshot.date
                    ))

        return instructions

    @staticmethod
    def calculate_liquidity(data: pd.DataFrame, lookback_period: int = 20) -> float:
        """计算流动性因子：平均成交额/市值的代理指标"""
        if len(data) < lookback_period:
            return np.nan

        recent_data = data.iloc[-lookback_period:]
        avg_turnover = (recent_data['volume'] * recent_data['close']).mean()
        avg_market_cap = recent_data['close'].mean() * 100000000  # 假设股本为1亿

        if avg_market_cap > 0:
            liquidity_ratio = avg_turnover / avg_market_cap
            return liquidity_ratio

        return np.nan

class CompositeSignalGenerator(SignalGenerator):
    """复合因子信号生成器 - 多因子组合策略"""

    def __init__(self, factors: List[str] = None, weights: List[float] = None):
        if factors is None:
            factors = ['momentum', 'mean_reversion', 'volatility', 'liquidity']
        if weights is None:
            weights = [0.25, 0.25, 0.25, 0.25]

        factor_str = '_'.join([f"{f}_{w}" for f, w in zip(factors, weights)])
        super().__init__(f"Composite_{factor_str}")
        self.factors = factors
        self.weights = weights

    def generate_signals(self, snapshot: DataSnapshot) -> List[TradingInstruction]:
        instructions = []

        for stock_code, factors in snapshot.factor_data.items():
            composite_score = 0.0
            valid_factors = 0

            for factor, weight in zip(self.factors, self.weights):
                factor_key = f"{factor}_score"
                if factor_key in factors and not pd.isna(factors[factor_key]):
                    composite_score += weight * factors[factor_key]
                    valid_factors += 1

            # 只考虑有足够因子数据的股票
            if valid_factors >= len(self.factors) * 0.5 and composite_score > 0.3:
                instructions.append(TradingInstruction(
                    stock_code=stock_code,
                    action='BUY',
                    quantity=1000,
                    reason=f"Composite Score: {composite_score:.4f}",
                    timestamp=snapshot.date
                ))

        return instructions

class AdvancedFactorHunter:
    """高级因子狩猎器 - 系统性测试多种因子"""

    def __init__(self, data_dir: str = "data/historical/stocks/complete_csi800/stocks"):
        self.data_dir = Path(data_dir)
        self.results_dir = Path("advanced_factor_hunt_results")
        self.results_dir.mkdir(exist_ok=True)

    def enhance_data_snapshot_with_advanced_factors(self, snapshot: DataSnapshot) -> DataSnapshot:
        """为数据快照添加高级因子数据"""
        enhanced_factor_data = {}

        for stock_code, stock_data in snapshot.stock_data.items():
            enhanced_factor_data[stock_code] = {}

            # 获取历史数据用于计算因子
            data = self._load_stock_historical_data(stock_code, snapshot.date)
            if data is None or len(data) < 30:
                continue

            # 计算各种因子
            factors = {
                'momentum_score': MomentumSignalGenerator.calculate_momentum(data, 20),
                'momentum_60d': MomentumSignalGenerator.calculate_momentum(data, 60),
                'mean_reversion_score': MeanReversionSignalGenerator.calculate_mean_reversion(data, 20),
                'volatility_score': VolatilitySignalGenerator.calculate_volatility(data, 20),
                'liquidity_score': LiquiditySignalGenerator.calculate_liquidity(data, 20),
            }

            # 计算复合因子
            valid_scores = [v for k, v in factors.items() if not pd.isna(v)]
            if len(valid_scores) >= 3:
                # 标准化并计算复合得分
                normalized_scores = [(s - min(valid_scores)) / (max(valid_scores) - min(valid_scores) + 1e-8) for s in valid_scores]
                factors['composite_score'] = np.mean(normalized_scores)

            enhanced_factor_data[stock_code].update(factors)

        # 计算横截面排序因子（如波动率排名）
        self._calculate_cross_sectional_ranks(enhanced_factor_data)

        return DataSnapshot(
            date=snapshot.date,
            stock_data=snapshot.stock_data,
            market_data=snapshot.market_data,
            factor_data=enhanced_factor_data,
            is_valid=snapshot.is_valid
        )

    def _calculate_cross_sectional_ranks(self, factor_data: Dict[str, Dict]):
        """计算横截面排序因子"""
        # 计算波动率排名
        volatilities = []
        for stock_code, factors in factor_data.items():
            if 'volatility_score' in factors and not pd.isna(factors['volatility_score']):
                volatilities.append((stock_code, factors['volatility_score']))

        if len(volatilities) > 10:
            volatilities.sort(key=lambda x: x[1])
            for rank, (stock_code, _) in enumerate(volatilities):
                factor_data[stock_code]['volatility_rank'] = rank / len(volatilities)

    def _load_stock_historical_data(self, stock_code: str, current_date: str) -> pd.DataFrame:
        """加载个股历史数据"""
        try:
            # 获取年份 - 支持字符串和日期格式
            if isinstance(current_date, str):
                year = current_date.split('-')[0]
                current_dt = pd.to_datetime(current_date)
            else:
                year = str(current_date.year)
                current_dt = current_date

            file_path = self.data_dir / year / f"{stock_code}.csv"

            if file_path.exists():
                data = pd.read_csv(file_path)
                data['date'] = pd.to_datetime(data['date'])

                # 获取当前日期之前的数据
                historical_data = data[data['date'] <= current_dt].copy()

                return historical_data
        except Exception as e:
            logger.warning(f"加载 {stock_code} 历史数据失败: {e}")

        return None

    def run_advanced_factor_tests(self, stock_codes: List[str], start_date: str, end_date: str) -> Dict[str, Any]:
        """运行高级因子测试"""
        logger.info(f"开始高级因子测试: {len(stock_codes)} 只股票, {start_date} 到 {end_date}")

        # 定义要测试的因子生成器
        factor_generators = [
            ("Momentum_20days_0.05", MomentumSignalGenerator(20, 0.05)),
            ("Momentum_60days_0.10", MomentumSignalGenerator(60, 0.10)),
            ("MeanReversion_20days_2std", MeanReversionSignalGenerator(20, 2.0)),
            ("LowVolatility_20days_0.3", VolatilitySignalGenerator(20, 0.3)),
            ("Liquidity_20days_0.5", LiquiditySignalGenerator(20, 0.5)),
        ]

        results = {}

        for factor_name, generator in factor_generators:
            logger.info(f"测试因子: {factor_name}")

            try:
                result = self.run_single_factor_test(factor_name, generator, stock_codes, start_date, end_date)
                results[factor_name] = result

                # 保存单个因子结果
                self._save_factor_result(factor_name, result)

            except Exception as e:
                logger.error(f"因子 {factor_name} 测试失败: {e}")
                results[factor_name] = {"error": str(e)}

        # 生成综合报告
        self._generate_comprehensive_report(results)

        return results

    def run_single_factor_test(self, factor_name: str, generator: SignalGenerator,
                              stock_codes: List[str], start_date: str, end_date: str) -> Dict[str, Any]:
        """运行单个因子测试"""

        class CustomBacktestEngine(BiasFreeBacktestEngine):
            def __init__(self, factor_hunter):
                super().__init__()
                self.factor_hunter = factor_hunter

            def create_data_snapshot(self, date, stock_data):
                basic_snapshot = super().create_data_snapshot(date, stock_data)
                enhanced_snapshot = self.factor_hunter.enhance_data_snapshot_with_advanced_factors(basic_snapshot)
                return enhanced_snapshot

        custom_engine = CustomBacktestEngine(self)
        custom_engine.add_signal_generator(generator)

        results = custom_engine.run_bias_free_backtest(stock_codes, start_date, end_date)

        return results

    def _serialize_result(self, obj):
        """递归序列化结果对象，处理不可序列化的对象"""
        if isinstance(obj, dict):
            return {k: self._serialize_result(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_result(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            # 处理自定义对象
            return str(obj)
        elif hasattr(obj, 'isoformat'):  # datetime对象
            return obj.isoformat()
        else:
            return obj

    def _save_factor_result(self, factor_name: str, result: Dict[str, Any]):
        """保存单个因子测试结果"""
        result_file = self.results_dir / f"{factor_name}_results.json"

        # 序列化结果
        serializable_result = self._serialize_result(result)

        # 添加元数据
        result_with_meta = {
            "factor_name": factor_name,
            "test_time": datetime.now().isoformat(),
            "results": serializable_result
        }

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_with_meta, f, indent=2, ensure_ascii=False)

        logger.info(f"因子 {factor_name} 结果已保存到 {result_file}")

    def _generate_comprehensive_report(self, results: Dict[str, Any]):
        """生成综合测试报告"""
        report_lines = []
        report_lines.append("# Advanced Factor Hunt Report - 高级因子搜索报告")
        report_lines.append("=" * 80)
        report_lines.append(f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"**测试因子数量**: {len(results)}")
        report_lines.append("")

        # 统计结果
        successful_tests = 0
        failed_tests = 0
        factor_performance = []

        for factor_name, result in results.items():
            if "error" in result:
                failed_tests += 1
                report_lines.append(f"### ❌ {factor_name}")
                report_lines.append(f"**错误**: {result['error']}")
                report_lines.append("")
            else:
                successful_tests += 1
                performance = result.get('total_return', 0)
                sharpe = result.get('sharpe_ratio', 0)
                max_drawdown = result.get('max_drawdown', 0)

                factor_performance.append({
                    'name': factor_name,
                    'return': performance,
                    'sharpe': sharpe,
                    'max_dd': max_drawdown
                })

                # 有效性评分
                effectiveness_score = 0
                if performance > 5:
                    effectiveness_score += 30
                elif performance > 0:
                    effectiveness_score += 15

                if sharpe > 1:
                    effectiveness_score += 40
                elif sharpe > 0.5:
                    effectiveness_score += 20
                elif sharpe > 0:
                    effectiveness_score += 10

                if max_drawdown < 10:
                    effectiveness_score += 30
                elif max_drawdown < 20:
                    effectiveness_score += 15

                recommendation = "ACCEPT" if effectiveness_score >= 60 else "REJECT"

                report_lines.append(f"### {'✅' if effectiveness_score >= 60 else '🟡'} {factor_name}")
                report_lines.append(f"**年化收益**: {performance:.2f}%")
                report_lines.append(f"**夏普比率**: {sharpe:.2f}")
                report_lines.append(f"**最大回撤**: {max_drawdown:.2f}%")
                report_lines.append(f"**有效性评分**: {effectiveness_score}/100")
                report_lines.append(f"**建议**: {recommendation}")
                report_lines.append("")

        # 性能排名
        if factor_performance:
            factor_performance.sort(key=lambda x: x['return'], reverse=True)
            report_lines.append("## 📊 因子性能排名")
            report_lines.append("")
            report_lines.append("| 排名 | 因子名称 | 年化收益 | 夏普比率 | 最大回撤 |")
            report_lines.append("|------|----------|----------|----------|----------|")

            for i, factor in enumerate(factor_performance, 1):
                report_lines.append(f"| {i} | {factor['name']} | {factor['return']:.2f}% | {factor['sharpe']:.2f} | {factor['max_dd']:.2f}% |")
            report_lines.append("")

        # 总结
        report_lines.append("## 🎯 测试总结")
        report_lines.append(f"**成功测试**: {successful_tests}")
        report_lines.append(f"**失败测试**: {failed_tests}")
        report_lines.append("")

        if factor_performance:
            best_factor = factor_performance[0]
            report_lines.append(f"**最佳因子**: {best_factor['name']} (年化收益: {best_factor['return']:.2f}%)")

            # 找出正收益的因子
            positive_factors = [f for f in factor_performance if f['return'] > 0]
            if positive_factors:
                report_lines.append(f"**正收益因子数量**: {len(positive_factors)}/{len(factor_performance)}")
            else:
                report_lines.append("**⚠️ 关键发现**: 所有因子都未能产生正收益，需要重新审视策略")

        report_lines.append("")
        report_lines.append("---")
        report_lines.append(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("*基于无偏差回测引擎的严格测试*")

        # 保存报告
        report_file = self.results_dir / "advanced_factor_hunt_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))

        logger.info(f"综合报告已保存到 {report_file}")

def main():
    """主函数"""
    # 创建高级因子狩猎器
    hunter = AdvancedFactorHunter()

    # 定义测试参数
    stock_codes = ['000001', '000002', '600036', '600519', '000858']  # 测试股票组合
    start_date = '2022-01-01'
    end_date = '2023-12-31'

    logger.info("开始高级因子搜索测试...")

    # 运行测试
    results = hunter.run_advanced_factor_tests(stock_codes, start_date, end_date)

    logger.info("高级因子搜索测试完成！")
    logger.info(f"结果保存在: {hunter.results_dir}")

if __name__ == "__main__":
    main()