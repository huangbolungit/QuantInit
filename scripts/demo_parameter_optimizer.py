#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parameter Optimizer Demo - 参数优化框架演示
快速展示参数优化框架的核心功能
"""

import os
import sys
import subprocess
import json
from pathlib import Path
import logging

# 添加项目路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_demo():
    """运行参数优化框架演示"""
    logger.info("🚀 参数优化框架演示")
    logger.info("=" * 50)

    # 演示1: 基础命令行参数网格
    logger.info("📊 演示1: 基础命令行参数网格")
    logger.info("命令: python scripts/parameter_optimizer.py --grid lookback_period=5,10 --quiet")

    try:
        result = subprocess.run([
            "python", "scripts/parameter_optimizer.py",
            "--grid", "lookback_period=5,10",
            "--quiet"
        ], capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            logger.info("✅ 演示1成功完成")
        else:
            logger.error(f"❌ 演示1失败: {result.stderr}")
    except subprocess.TimeoutExpired:
        logger.error("❌ 演示1超时")
    except Exception as e:
        logger.error(f"❌ 演示1出错: {e}")

    # 演示2: 帮助信息
    logger.info("\n📋 演示2: 帮助信息")
    logger.info("命令: python scripts/parameter_optimizer.py --help")

    try:
        result = subprocess.run([
            "python", "scripts/parameter_optimizer.py",
            "--help"
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            logger.info("✅ 帮助信息显示成功")
            # 显示帮助信息的前几行
            help_lines = result.stdout.split('\n')[:10]
            for line in help_lines:
                if line.strip():
                    logger.info(f"  {line}")
        else:
            logger.error(f"❌ 帮助信息显示失败: {result.stderr}")
    except Exception as e:
        logger.error(f"❌ 帮助信息显示出错: {e}")

    # 演示3: 检查生成的文件
    logger.info("\n📁 演示3: 检查生成的结果文件")

    results_dir = Path("optimization_results")
    if results_dir.exists():
        files = list(results_dir.glob("*"))
        logger.info(f"✅ 找到 {len(files)} 个结果文件:")

        for file_path in sorted(files):
            if file_path.is_file():
                size = file_path.stat().st_size
                logger.info(f"  📄 {file_path.name} ({size:,} bytes)")

                # 显示文件内容的简要信息
                if file_path.suffix == '.md':
                    try:
                        content = file_path.read_text(encoding='utf-8')
                        lines = content.split('\n')
                        title_line = next((line for line in lines if line.startswith('#')), '')
                        if title_line:
                            logger.info(f"    标题: {title_line}")
                    except Exception as e:
                        logger.warning(f"    无法读取文件内容: {e}")

                elif file_path.suffix == '.csv':
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            header = f.readline().strip()
                            logger.info(f"    CSV表头: {header}")
                    except Exception as e:
                        logger.warning(f"    无法读取CSV文件: {e}")

                elif file_path.suffix == '.json':
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            strategy_name = data.get('strategy_name', 'Unknown')
                            total_combinations = data.get('total_combinations', 0)
                            successful_tests = data.get('successful_tests', 0)
                            logger.info(f"    策略: {strategy_name}")
                            logger.info(f"    测试: {successful_tests}/{total_combinations}")
                    except Exception as e:
                        logger.warning(f"    无法读取JSON文件: {e}")
    else:
        logger.warning("❌ 结果目录不存在")

    # 演示4: 配置文件验证
    logger.info("\n⚙️ 演示4: 配置文件验证")

    config_file = Path("config/params.json")
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            logger.info("✅ 配置文件格式正确")
            logger.info(f"  策略名称: {config.get('strategy_name', 'Unknown')}")

            parameter_grid = config.get('parameter_grid', {})
            total_combinations = 1
            for param, values in parameter_grid.items():
                total_combinations *= len(values)
                logger.info(f"  参数 {param}: {len(values)} 个值")

            logger.info(f"  总组合数: {total_combinations}")

        except json.JSONDecodeError as e:
            logger.error(f"❌ 配置文件JSON格式错误: {e}")
        except Exception as e:
            logger.error(f"❌ 配置文件读取失败: {e}")
    else:
        logger.warning("❌ 配置文件不存在")

    logger.info("\n🎉 参数优化框架演示完成!")
    logger.info("=" * 50)
    logger.info("📖 更多使用方法请查看: docs/parameter_optimizer_usage.md")

if __name__ == "__main__":
    run_demo()
