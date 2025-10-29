# A股智能投顾助手 (MVP) - 技术规格文档 (SPEC)

**版本**: v0.2-MVP
**更新时间**: 2025年10月18日
**文档状态**: 定稿

## 1. 技术架构

*   **架构模式**: 采用**前后端分离**的B/S架构，所有服务均在本机运行。
    *   **后端 (Backend)**: Python 3.9+，负责数据获取、因子计算、AI分析、策略决策和通过API/WebSocket提供服务。
    *   **前端 (Frontend)**: 现代浏览器，通过HTML/CSS/JavaScript构建用户界面，与后端实时通信。
*   **技术选型**:
    *   **后端框架**: **FastAPI**。理由：原生支持异步IO，性能高，非常适合处理并发的API请求和WebSocket长连接。
    *   **数据获取**: `httpx` (异步HTTP库)。
    *   **实时通信**: **FastAPI内置的WebSocket**。用于后端向前端实时推送市场更新、新闻警报和股票池建议。
    *   **定时任务/后台作业**: `apscheduler`。用于定时运行因子评分引擎和新闻扫描任务。
    *   **AI模型接口**: `httpx` 调用GLM-4.6的HTTP API。
    *   **数据持久化**: **SQLite**。轻量级，无需配置，用于存储股票池列表、历史建议、因子得分、模拟交易指令等。
    *   **数据分析库**: `Pandas`, `NumPy`。用于高效处理和计算量化因子。
    *   **前端框架**: **Vue.js 3 (Composition API)**。理由：响应式数据绑定非常适合构建数据驱动的仪表盘，组件化开发能让结构更清晰。
    *   **图表库**: `Apache ECharts`。功能强大，图表类型丰富，适合渲染专业的K线图。

## 2. 核心逻辑实现：多因子评分引擎

这是系统的技术核心，负责将原始数据转化为决策依据。

### 2.1. 因子库定义 (Factor Library)
在代码层面，可以定义一个`factors`模块，包含各类因子的计算函数。
*   **`momentum_factors.py`**:
    *   `calc_ma_score(data)`: 计算均线排列得分。
    *   `calc_rsi_score(data)`: 计算相对强弱指标得分。
*   **`sentiment_factors.py`**:
    *   `calc_news_score(stock_code)`: 从数据库读取新闻分析结果，转化为事件得分。
    *   `calc_turnover_score(data)`: 计算换手率异动得分。
*   **`value_factors.py`**:
    *   `calc_pe_percentile_score(data)`: 计算PE在行业内的百分位得分。

### 2.2. 评分与排名引擎 (Scoring Engine)
这是一个核心的后台服务，由`apscheduler`定时触发。
1.  **数据准备**: 从数据源获取所有候选股的日K线、资金流向、基本面等原始数据。
2.  **因子计算**: 遍历所有股票，调用因子库中的函数，计算每个因子的原始值。
3.  **因子归一化 (Normalization)**:
    *   对所有股票的同一因子值进行横向比较。
    *   使用`pandas.qcut`或`rank(pct=True)`等函数，将每个因子的原始值转化为0-100的百分位排名得分。这是确保不同因子可比性的关键。
4.  **加权与综合评分**:
    *   根据预设的权重（如：`{'momentum': 0.4, 'sentiment': 0.3, ...}`）对归一化后的因子分进行加权求和，得到每只股票的最终**综合评分**。
    *   将所有股票的评分结果存入SQLite数据库，覆盖旧的评分。

### 2.3. 建议生成规则 (Suggestion Engine)
在评分引擎执行完毕后，触发此引擎。
1.  **读取新旧评分**: 同时从数据库读取本次和上次的综合评分。
2.  **扫描入池信号**: 遍历所有评分，寻找满足“建议加入”规则的股票（例如：`new_score >= 90 AND old_score < 90`）。
3.  **扫描出池信号**: 遍历当前股票池内的股票，检查是否满足“建议移出”规则（例如：`new_score < 80`或触发硬性止损）。
4.  **生成与推送**: 对于满足条件的股票，生成结构化的建议（包含理由），存入数据库，并通过WebSocket推送给前端。

## 3. API与WebSocket接口设计

### 3.1. REST API
*   `GET /api/market/overview`: 一次性获取市场情绪、板块热力图等初始化数据。
*   `GET /api/stock-list/{sector_name}`: 获取指定板块的个股列表。
*   `GET /api/stock-pool`: 获取当前股票池列表及详情。
*   `GET /api/kline/{stock_code}`: 获取指定股票的K线数据。
*   `POST /api/pool-suggestion/confirm`: 用户确认调仓建议。

### 3.2. WebSocket 事件
*   **命名空间**: `/realtime`
*   **后端 -> 前端**:
    *   `market_update`: 定时推送最新的市场情绪和板块热力数据。
    *   `news_alert`: 推送一条新闻及其AI分析结果。
    *   `pool_suggestion`: 推送一条新的股票池调仓建议。
    *   `pool_updated`: 当股票池发生变化后，推送完整的最新股票池列表。

## 4. MVP部署与运行
1.  **环境设置**: 安装Python, Node.js。创建`.env`文件存放API密钥。
2.  **启动后端**: `uvicorn main:app --reload`
3.  **启动前端**: `cd frontend && npm run serve`
4.  **访问**: 在浏览器中打开 `http://localhost:8080` (或其他前端端口)。