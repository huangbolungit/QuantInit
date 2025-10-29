#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BaoStock数据获取客户端
专为CSI300成分股数据下载优化的BaoStock接口
"""

import baostock as bs
import pandas as pd
import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import os
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BaoStockClient:
    """
    BaoStock数据获取客户端
    提供CSI300成分股数据下载、历史数据获取等功能
    """

    def __init__(self):
        """初始化BaoStock客户端"""
        self.session = None
        self.is_logged_in = False
        self.login_attempts = 0
        self.max_login_attempts = 3

        # 数据存储目录
        self.data_dir = Path("backend/data/historical/stocks")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 统计信息
        self.stats = {
            'login_count': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'total_records': 0,
            'start_time': datetime.now()
        }

        logger.info("🚀 BaoStock客户端初始化完成")

    def login(self) -> bool:
        """
        登录BaoStock系统

        Returns:
            bool: 登录是否成功
        """
        if self.is_logged_in:
            return True

        self.login_attempts += 1

        try:
            logger.info("🔐 正在登录BaoStock系统...")
            lg = bs.login()

            if lg.error_code == '0':
                self.session = lg
                self.is_logged_in = True
                self.stats['login_count'] += 1
                logger.info(f"✅ BaoStock登录成功 - {lg.error_msg}")
                return True
            else:
                logger.error(f"❌ BaoStock登录失败 - {lg.error_msg}")
                return False

        except Exception as e:
            logger.error(f"❌ BaoStock登录异常 - {e}")
            return False

    def logout(self) -> bool:
        """
        登出BaoStock系统

        Returns:
            bool: 登出是否成功
        """
        if not self.is_logged_in:
            return True

        try:
            lg = bs.logout()
            self.is_logged_in = False
            self.session = None
            logger.info("✅ BaoStock登出成功")
            return lg.error_code == '0'

        except Exception as e:
            logger.error(f"❌ BaoStock登出异常 - {e}")
            return False

    def get_csi300_constituents(self) -> Optional[pd.DataFrame]:
        """
        获取沪深300成分股列表

        Returns:
            pd.DataFrame: CSI300成分股数据，包含code, code_name, updateDate
        """
        if not self._ensure_login():
            return None

        try:
            logger.info("📊 获取沪深300成分股列表...")
            rs = bs.query_hs300_stocks()

            if rs.error_code == '0':
                data = rs.get_data()
                logger.info(f"✅ 成功获取 {len(data)} 只沪深300成分股")
                self.stats['successful_queries'] += 1
                return data
            else:
                logger.error(f"❌ 获取CSI300成分股失败 - {rs.error_msg}")
                self.stats['failed_queries'] += 1
                return None

        except Exception as e:
            logger.error(f"❌ 获取CSI300成分股异常 - {e}")
            self.stats['failed_queries'] += 1
            return None

    def get_csi500_constituents(self) -> Optional[pd.DataFrame]:
        """
        获取中证500成分股列表

        Returns:
            pd.DataFrame: CSI500成分股数据，包含code, code_name, updateDate
        """
        if not self._ensure_login():
            return None

        try:
            logger.info("📊 获取中证500成分股列表...")
            rs = bs.query_zz500_stocks()

            if rs.error_code == '0':
                data = rs.get_data()
                logger.info(f"✅ 成功获取 {len(data)} 只中证500成分股")
                self.stats['successful_queries'] += 1
                return data
            else:
                logger.error(f"❌ 获取CSI500成分股失败 - {rs.error_msg}")
                self.stats['failed_queries'] += 1
                return None

        except Exception as e:
            logger.error(f"❌ 获取CSI500成分股异常 - {e}")
            self.stats['failed_queries'] += 1
            return None

    def download_stock_data(self,
                          stock_code: str,
                          start_date: str = '2020-01-01',
                          end_date: str = None,
                          fields: str = None) -> Optional[pd.DataFrame]:
        """
        下载单只股票的历史数据

        Args:
            stock_code: 股票代码，如 'sh.600000'
            start_date: 开始日期，默认 '2020-01-01'
            end_date: 结束日期，默认今天
            fields: 数据字段，默认包含OHLCV及基本面数据

        Returns:
            pd.DataFrame: 股票历史数据
        """
        if not self._ensure_login():
            return None

        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        # 默认字段：基础数据 + 基本面指标
        if fields is None:
            fields = 'date,code,open,high,low,close,volume,amount,adjustflag,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM'

        try:
            # 添加延迟以避免过快请求
            time.sleep(0.1)

            logger.debug(f"📥 下载 {stock_code} 数据 ({start_date} 到 {end_date})")
            rs = bs.query_history_k_data_plus(stock_code, fields, start_date=start_date, end_date=end_date)

            if rs.error_code == '0':
                data = rs.get_data()

                if len(data) > 0:
                    # 数据清洗和格式化
                    data = self._clean_data(data)
                    self.stats['total_records'] += len(data)
                    self.stats['successful_queries'] += 1
                    logger.debug(f"✅ {stock_code} 下载成功: {len(data)} 条记录")
                    return data
                else:
                    logger.warning(f"⚠️ {stock_code} 无数据")
                    return None
            else:
                logger.error(f"❌ {stock_code} 下载失败 - {rs.error_msg}")
                self.stats['failed_queries'] += 1
                return None

        except Exception as e:
            logger.error(f"❌ {stock_code} 下载异常 - {e}")
            self.stats['failed_queries'] += 1
            return None

    def download_multiple_stocks(self,
                               stock_codes: List[str],
                               start_date: str = '2020-01-01',
                               end_date: str = None,
                               save_to_file: bool = True,
                               max_concurrent: int = 1) -> Dict[str, Any]:
        """
        批量下载多只股票数据

        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            save_to_file: 是否保存到文件
            max_concurrent: 最大并发数（BaoStock建议单线程）

        Returns:
            Dict: 下载结果统计
        """
        if not self._ensure_login():
            return {'success': False, 'error': 'Login failed'}

        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        results = {
            'total_stocks': len(stock_codes),
            'successful': 0,
            'failed': 0,
            'no_data': 0,
            'total_records': 0,
            'failed_stocks': [],
            'start_time': datetime.now()
        }

        logger.info(f"📦 开始批量下载 {len(stock_codes)} 只股票数据...")

        for i, stock_code in enumerate(stock_codes, 1):
            try:
                logger.info(f"📊 [{i}/{len(stock_codes)}] 下载 {stock_code}...")

                # 下载数据
                data = self.download_stock_data(stock_code, start_date, end_date)

                if data is not None and len(data) > 0:
                    results['successful'] += 1
                    results['total_records'] += len(data)

                    # 保存到文件
                    if save_to_file:
                        self._save_stock_data(data, stock_code)

                    logger.info(f"✅ {stock_code} 成功: {len(data)} 条记录")

                elif data is not None and len(data) == 0:
                    results['no_data'] += 1
                    logger.warning(f"⚠️ {stock_code} 无数据")

                else:
                    results['failed'] += 1
                    results['failed_stocks'].append(stock_code)
                    logger.error(f"❌ {stock_code} 下载失败")

                # 进度报告
                if i % 10 == 0 or i == len(stock_codes):
                    progress = i / len(stock_codes) * 100
                    logger.info(f"📈 进度: {i}/{len(stock_codes)} ({progress:.1f}%) - "
                              f"成功: {results['successful']}, 失败: {results['failed']}, "
                              f"无数据: {results['no_data']}")

            except Exception as e:
                results['failed'] += 1
                results['failed_stocks'].append(stock_code)
                logger.error(f"❌ {stock_code} 处理异常 - {e}")

        # 最终统计
        results['end_time'] = datetime.now()
        results['duration'] = results['end_time'] - results['start_time']
        results['success_rate'] = results['successful'] / len(stock_codes) * 100

        self._log_download_summary(results)
        return results

    def download_csi300_complete(self,
                                start_date: str = '2020-01-01',
                                end_date: str = None,
                                save_to_file: bool = True) -> Dict[str, Any]:
        """
        下载完整的CSI300成分股数据

        Args:
            start_date: 开始日期
            end_date: 结束日期
            save_to_file: 是否保存到文件

        Returns:
            Dict: 下载结果统计
        """
        logger.info("🎯 开始下载完整CSI300成分股数据...")

        # 获取CSI300成分股列表
        csi300_data = self.get_csi300_constituents()
        if csi300_data is None:
            return {'success': False, 'error': 'Failed to get CSI300 constituents'}

        stock_codes = csi300_data['code'].tolist()
        logger.info(f"📋 获取到 {len(stock_codes)} 只CSI300成分股")

        # 批量下载
        results = self.download_multiple_stocks(
            stock_codes=stock_codes,
            start_date=start_date,
            end_date=end_date,
            save_to_file=save_to_file
        )

        results['csi300_info'] = csi300_data.to_dict('records')
        results['success'] = results['successful'] > 0

        return results

    def get_session_stats(self) -> Dict[str, Any]:
        """获取当前会话统计信息"""
        current_time = datetime.now()
        session_duration = current_time - self.stats['start_time']

        return {
            'session_duration': str(session_duration),
            'login_count': self.stats['login_count'],
            'successful_queries': self.stats['successful_queries'],
            'failed_queries': self.stats['failed_queries'],
            'total_records': self.stats['total_records'],
            'success_rate': (
                self.stats['successful_queries'] /
                (self.stats['successful_queries'] + self.stats['failed_queries']) * 100
                if (self.stats['successful_queries'] + self.stats['failed_queries']) > 0
                else 0
            ),
            'is_logged_in': self.is_logged_in
        }

    # === 私有方法 ===

    def _ensure_login(self) -> bool:
        """确保已登录"""
        if not self.is_logged_in:
            return self.login()
        return True

    def _clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        清洗和格式化数据

        Args:
            data: 原始数据

        Returns:
            pd.DataFrame: 清洗后的数据
        """
        # 转换日期格式
        if 'date' in data.columns:
            data['date'] = pd.to_datetime(data['date'])

        # 转换数值列
        numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'amount',
                          'turn', 'pctChg', 'peTTM', 'pbMRQ', 'psTTM', 'pcfNcfTTM']

        for col in numeric_columns:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')

        # 排序
        if 'date' in data.columns:
            data = data.sort_values('date').reset_index(drop=True)

        return data

    def _save_stock_data(self, data: pd.DataFrame, stock_code: str):
        """
        保存股票数据到文件

        Args:
            data: 股票数据
            stock_code: 股票代码
        """
        try:
            # 创建以年份分类的目录结构
            data['year'] = data['date'].dt.year
            years = data['year'].unique()

            for year in years:
                year_data = data[data['year'] == year].copy()
                year_dir = self.data_dir / f"csi300_baostock_{year}" / "stocks"
                year_dir.mkdir(parents=True, exist_ok=True)

                # 文件名：6位股票代码.csv
                filename = f"{stock_code.split('.')[1]}.csv"
                filepath = year_dir / filename

                # 删除year列
                year_data = year_data.drop('year', axis=1)

                # 如果文件已存在，检查是否需要更新
                if filepath.exists():
                    existing_data = pd.read_csv(filepath)
                    existing_data['date'] = pd.to_datetime(existing_data['date'])

                    # 合并数据，去重
                    combined_data = pd.concat([existing_data, year_data])
                    combined_data = combined_data.drop_duplicates(subset=['date'], keep='last')
                    combined_data = combined_data.sort_values('date').reset_index(drop=True)

                    combined_data.to_csv(filepath, index=False, encoding='utf-8')
                else:
                    year_data.to_csv(filepath, index=False, encoding='utf-8')

                logger.debug(f"💾 保存 {stock_code} {year}年数据到 {filepath}")

        except Exception as e:
            logger.error(f"❌ 保存 {stock_code} 数据失败 - {e}")

    def _log_download_summary(self, results: Dict[str, Any]):
        """记录下载摘要"""
        logger.info("=" * 60)
        logger.info("📊 下载完成统计:")
        logger.info(f"  总股票数: {results['total_stocks']}")
        logger.info(f"  成功下载: {results['successful']} ({results['success_rate']:.1f}%)")
        logger.info(f"  下载失败: {results['failed']}")
        logger.info(f"  无数据: {results['no_data']}")
        logger.info(f"  总记录数: {results['total_records']:,}")
        logger.info(f"  用时: {results['duration']}")

        if results['failed_stocks']:
            logger.warning(f"  失败股票: {', '.join(results['failed_stocks'][:10])}...")

        logger.info("=" * 60)

    def _convert_to_baostock_format(self, stock_code: str) -> str:
        """
        将股票代码转换为BaoStock格式

        Args:
            stock_code: 股票代码，支持 '600000' 或 'sh.600000' 格式

        Returns:
            str: BaoStock格式，如 'sh.600000'
        """
        try:
            # 如果已经是BaoStock格式
            if isinstance(stock_code, str) and (stock_code.startswith('sh.') or stock_code.startswith('sz.')):
                return stock_code.lower()

            # 确保是字符串格式
            code = str(stock_code).strip().zfill(6)

            # 根据股票代码判断交易所
            if code.startswith(('000', '001', '002', '003', '300')):
                return f"sz.{code}"
            elif code.startswith(('600', '601', '603', '605', '688', '695')):
                return f"sh.{code}"
            else:
                # 默认处理：未知代码分配到深圳
                logger.warning(f"未知交易所代码: {code}，默认分配到深圳交易所")
                return f"sz.{code}"

        except Exception as e:
            logger.error(f"股票代码格式转换失败 {stock_code}: {e}")
            # 默认返回深圳格式
            return f"sz.{str(stock_code).strip().zfill(6)}"


def main():
    """测试函数"""
    client = BaoStockClient()

    try:
        # 测试登录
        if client.login():
            print("✅ 登录测试成功")

            # 测试获取CSI300成分股
            csi300 = client.get_csi300_constituents()
            if csi300 is not None:
                print(f"✅ 获取CSI300成分股成功: {len(csi300)} 只")
                print(csi300.head())

                # 测试下载单只股票
                test_codes = ['sh.600000', 'sz.000001']
                results = client.download_multiple_stocks(
                    test_codes,
                    start_date='2024-12-01',
                    end_date='2024-12-31'
                )
                print(f"✅ 批量下载测试: {results}")

            # 显示统计信息
            stats = client.get_session_stats()
            print(f"📊 会话统计: {stats}")

        else:
            print("❌ 登录测试失败")

    finally:
        client.logout()


if __name__ == "__main__":
    main()