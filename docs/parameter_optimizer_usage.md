# 参数优化框架使用指南

## 概述

这是一个生产级的参数优化框架，专为A股智能投顾助手设计。支持命令行接口、JSON配置网格、多格式输出等功能。

## 主要特性

- ✅ **命令行接口**: 支持 `--grid` 和 `--grid-file` 两种参数配置方式
- ✅ **灵活配置**: 支持自定义数据目录、输出目录、调频周期、股票池
- ✅ **多格式输出**: JSON详细结果、CSV摘要、Markdown报告
- ✅ **调频支持**: 5日、10日、20日调频周期选择
- ✅ **股票池配置**: 自定义股票代码组合
- ✅ **综合评分**: 基于收益、夏普比率、回撤、交易活跃度的综合评分
- ✅ **错误处理**: 完善的错误处理和日志记录

## 安装依赖

```bash
pip install pandas numpy
```

## 基本用法

### 1. 命令行参数网格

命令行模式使用 `参数名=取值列表` 的形式，可以一次指定多个参数维度：

**单参数优化:**
```bash
python scripts/parameter_optimizer.py --grid lookback_period=5,10,15,20
```

**多参数优化:**
```bash
python scripts/parameter_optimizer.py \
  --grid lookback_period=5,10,15 \
         buy_threshold=-0.03,-0.05,-0.08 \
         sell_threshold=0.02,0.03,0.05
```

### 2. JSON配置文件

**使用配置文件:**
```bash
python scripts/parameter_optimizer.py --grid-file config/params.json
```

配置文件示例：
```json
{
  "strategy_name": "OptimizedMeanReversion",
  "parameter_grid": {
    "lookback_period": [5, 10, 15, 20],
    "buy_threshold": [-0.03, -0.05, -0.08, -0.10],
    "sell_threshold": [0.02, 0.03, 0.05, 0.06]
  },
  "fixed_parameters": {
    "max_hold_days": 15
  }
}
```

### 3. 自定义配置

**自定义数据目录和输出目录:**
```bash
python scripts/parameter_optimizer.py --grid lookback_period=5,10,15 \
  --data-dir custom/data \
  --output-dir custom/results
```

**指定调频和股票池:**
```bash
python scripts/parameter_optimizer.py --grid lookback_period=5,10,15 \
  buy_threshold=-0.05,-0.08 \
  --rebalancing-freq 5 \
  --stock-pool 000001,600036,600519
```

## 命令行参数详解

### 必选参数

- `--grid`: 命令行参数网格，与 `--grid-file` 二选一
- `--grid-file`: JSON配置文件路径，与 `--grid` 二选一

### 可选参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--data-dir` | string | `data/historical/stocks/complete_csi800/stocks` | 历史数据目录 |
| `--output-dir` | string | `optimization_results` | 结果输出目录 |
| `--start-date` | string | `2022-01-01` | 回测开始日期 |
| `--end-date` | string | `2023-12-31` | 回测结束日期 |
| `--rebalancing-freq` | int | `10` | 调频周期 (5/10/20日) |
| `--stock-pool` | string | `000001,000002,600036,600519,000858` | 股票池代码 |
| `--verbose` | flag | False | 详细输出模式 |
| `--quiet` | flag | False | 静默模式 |

## 输出文件说明

参数优化完成后，会在输出目录生成以下文件：

### 1. JSON详细结果
- 文件名: `optimization_YYYYMMDD_HHMMSS.json`
- 内容: 完整的优化结果，包括所有参数组合的详细性能数据

### 2. CSV摘要
- 文件名: `optimization_YYYYMMDD_HHMMSS_summary.csv`
- 内容: 所有参数组合的性能摘要，单次运行生成独立文件
- 字段: 组合ID、得分、收益、夏普比率、回撤、交易次数、状态、参数值

### 3. Markdown报告
- 文件名: `optimization_YYYYMMDD_HHMMSS_report.md`
- 内容: 人类可读的优化报告，包含最佳参数组合和性能排名

## 评分机制

框架使用综合评分系统来评估参数组合：

```python
score = (total_return * 0.4 +
         sharpe_ratio * 20 * 0.3 -
         max_drawdown * 0.2 +
         min(trade_count / 100, 1) * 10 * 0.1)
```

评分权重：
- **总收益**: 40%
- **夏普比率**: 30% (放大20倍)
- **最大回撤**: 20% (惩罚项)
- **交易活跃度**: 10% (奖励项)

## 策略类型

当前支持的策略：

### OptimizedMeanReversion (优化均值回归策略)

**参数说明:**
- `lookback_period`: 均值回归计算窗口期
- `buy_threshold`: 买入阈值 (负数，表示低于均值的程度)
- `sell_threshold`: 卖出阈值 (正数，表示高于均值的程度)
- `max_hold_days`: 最大持有天数

**交易逻辑:**
- 买入: 当价格显著低于历史均值时
- 卖出: 当价格回归均值或达到止损/时间止损时

## 使用示例

### 示例1: 基础参数优化

```bash
python scripts/parameter_optimizer.py \
  --grid lookback_period=5,10,15 \
         buy_threshold=-0.03,-0.05,-0.08
```

### 示例2: 使用JSON配置文件

```bash
python scripts/parameter_optimizer.py --grid-file config/params.json \
  --rebalancing-freq 5 \
  --stock-pool 000001,600036,600519 \
  --verbose
```

### 示例3: 自定义时间范围

```bash
python scripts/parameter_optimizer.py --grid lookback_period=5,10,15 \
  --start-date 2021-01-01 \
  --end-date 2022-12-31
```

## 错误处理

框架包含完善的错误处理机制：

- **参数验证**: 自动验证命令行参数和JSON配置格式
- **数据检查**: 检查数据目录和股票数据完整性
- **异常捕获**: 捕获并记录单个参数组合的测试失败
- **优雅退出**: 支持Ctrl+C中断和错误状态码

## 性能优化建议

1. **合理设置参数范围**: 避免过大的参数网格导致计算时间过长
2. **使用静默模式**: 批量运行时使用 `--quiet` 减少输出
3. **分批优化**: 对于大型参数网格，考虑分批进行优化
4. **结果缓存**: 框架会保存所有结果，支持增量分析

## 扩展开发

### 添加新策略

1. 在 `scripts/parameter_optimizer.py` 中添加新策略类
2. 继承 `SignalGenerator` 基类
3. 实现 `generate_signals` 方法
4. 在 `create_strategy_from_config` 中添加策略创建逻辑

### 自定义评分函数

修改 `_calculate_score` 方法来自定义评分机制。

### 添加新参数类型

在JSON配置文件中添加新的参数网格维度。

## 故障排除

### 常见问题

1. **数据目录不存在**: 检查 `--data-dir` 参数指向的路径
2. **JSON格式错误**: 验证配置文件的JSON语法
3. **股票数据缺失**: 确保股票池中的股票在指定时间范围内有数据
4. **权限错误**: 确保对输出目录有写权限

### 调试技巧

1. 使用 `--verbose` 获取详细日志
2. 检查JSON结果文件中的错误信息
3. 查看Markdown报告中的失败组合统计

## 更新日志

- **v1.0.0**: 初始版本，支持基础参数优化功能
- 支持命令行和JSON配置
- 多格式输出 (JSON/CSV/Markdown)
- 综合评分系统
- 完善的错误处理

## 联系支持

如有问题或建议，请通过以下方式联系：
- 项目仓库: [A股智能投顾助手](https://github.com/your-repo)
- 问题反馈: 请在GitHub Issues中提交
- 技术支持: 请查看项目文档或联系开发团队
