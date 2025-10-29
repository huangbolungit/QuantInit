# A股智能投顾助手 - 精确实施计划

**版本**: v1.0
**制定时间**: 2025年10月18日
**基于文档**: PRD v0.2-MVP, SPEC v0.2-MVP, UI设计参考
**项目状态**: 绿地项目（需全新开发）

---

## 📊 项目概况与目标

### 产品定位
本地部署的量化投顾工具，基于多因子综合评分模型，为开发者本人提供专业、客观的股票投资决策辅助。

### 核心目标
1. **验证多因子评分策略**的有效性和实用性
2. **实现全流程技术验证**：数据获取→因子计算→AI分析→策略决策→实时推送→界面展示
3. **构建个人决策工具**：系统化辅助日常投资决策

---

## 🏗️ 技术架构设计

### 技术栈选型
```yaml
后端架构:
  框架: FastAPI (Python 3.9+)
  数据库: SQLite (轻量级本地部署)
  异步HTTP: httpx
  任务调度: APScheduler
  实时通信: WebSocket (FastAPI内置)
  AI集成: GLM-4.6 HTTP API
  数据处理: Pandas + NumPy

前端架构:
  框架: Vue.js 3 (Composition API)
  状态管理: Pinia
  图表库: Apache ECharts
  UI组件: Element Plus
  HTTP客户端: Axios
  实时通信: Socket.IO Client
```

### 项目目录结构
```
stock-advisor/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── api/               # API路由
│   │   │   ├── endpoints/     # REST API端点
│   │   │   │   ├── market.py
│   │   │   │   ├── stocks.py
│   │   │   │   ├── pool.py
│   │   │   │   └── news.py
│   │   │   └── websocket.py   # WebSocket处理器
│   │   ├── core/              # 核心配置
│   │   │   ├── config.py      # 配置管理
│   │   │   ├── database.py    # 数据库连接
│   │   │   └── security.py    # 安全配置
│   │   ├── models/            # 数据模型
│   │   │   ├── stock.py
│   │   │   ├── factor.py
│   │   │   ├── suggestion.py
│   │   │   └── news.py
│   │   ├── services/          # 业务逻辑
│   │   │   ├── data_sources/  # 数据源服务
│   │   │   │   ├── eastmoney.py
│   │   │   │   ├── sina.py
│   │   │   │   └── tencent.py
│   │   │   ├── factors/       # 因子计算
│   │   │   │   ├── momentum.py
│   │   │   │   ├── sentiment.py
│   │   │   │   ├── value.py
│   │   │   │   └── quality.py
│   │   │   ├── scoring/       # 评分引擎
│   │   │   │   ├── engine.py
│   │   │   │   └── ranking.py
│   │   │   ├── ai_analysis/   # AI分析服务
│   │   │   │   └── glm46_client.py
│   │   │   └── suggestions/   # 建议生成
│   │   │       └── engine.py
│   │   └── utils/             # 工具函数
│   │       ├── logger.py
│   │       ├── helpers.py
│   │       └── validators.py
│   ├── data/
│   │   └── database/
│   │       └── stocks.db      # SQLite数据库
│   ├── tests/
│   ├── requirements.txt
│   ├── .env.example
│   └── main.py               # 应用入口
├── frontend/                  # 前端应用
│   ├── src/
│   │   ├── components/       # 组件
│   │   │   ├── common/       # 通用组件
│   │   │   ├── market/       # 市场相关组件
│   │   │   ├── stocks/       # 股票相关组件
│   │   │   └── charts/       # 图表组件
│   │   ├── views/            # 页面视图
│   │   │   ├── Dashboard.vue
│   │   │   ├── StockPool.vue
│   │   │   ├── StockDetail.vue
│   │   │   └── NewsAnalysis.vue
│   │   ├── services/         # API服务
│   │   │   ├── api.js
│   │   │   ├── websocket.js
│   │   │   └── socket.js
│   │   ├── stores/           # 状态管理
│   │   │   ├── market.js
│   │   │   ├── stocks.js
│   │   │   └── news.js
│   │   ├── utils/            # 工具函数
│   │   │   ├── formatters.js
│   │   │   └── validators.js
│   │   ├── assets/           # 静态资源
│   │   ├── App.vue
│   │   └── main.js
│   ├── public/
│   ├── package.json
│   ├── vite.config.js
│   └── .env.example
├── docs/                     # 文档
│   ├── api/                  # API文档
│   └── deployment/           # 部署文档
├── scripts/                  # 脚本
│   ├── setup.sh             # 环境设置
│   ├── start.sh             # 启动脚本
│   └── backup.sh            # 数据备份
├── .gitignore
├── README.md
└── docker-compose.yml        # 可选：容器化部署
```

---

## 📋 数据库设计

### 核心表结构
```sql
-- 股票基础信息表
CREATE TABLE stocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    sector VARCHAR(50),
    industry VARCHAR(100),
    market VARCHAR(20), -- 'SZ', 'SH'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 股票池表
CREATE TABLE stock_pool (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    removed_at TIMESTAMP NULL,
    current_score FLOAT,
    entry_reason TEXT,
    exit_reason TEXT,
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'removed'
    FOREIGN KEY (stock_id) REFERENCES stocks(id)
);

-- 因子评分表
CREATE TABLE factor_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    date DATE NOT NULL,
    momentum_score FLOAT,      -- 动量因子得分
    sentiment_score FLOAT,     -- 情绪因子得分
    value_score FLOAT,         -- 价值因子得分
    quality_score FLOAT,       -- 质量因子得分
    total_score FLOAT,         -- 综合得分
    raw_data JSON,             -- 原始计算数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_id) REFERENCES stocks(id),
    UNIQUE(stock_id, date)
);

-- 调仓建议表
CREATE TABLE suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    action VARCHAR(10) NOT NULL, -- 'ADD', 'REMOVE'
    reason TEXT NOT NULL,
    score FLOAT,
    key_factors JSON,           -- 关键影响因子
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'confirmed', 'ignored'
    user_action VARCHAR(20),    -- 用户操作
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP NULL,
    FOREIGN KEY (stock_id) REFERENCES stocks(id)
);

-- 新闻分析表
CREATE TABLE news_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    sentiment VARCHAR(20),      -- 'positive', 'negative', 'neutral'
    related_sectors JSON,       -- 关联板块
    related_stocks JSON,        -- 关联股票
    impact_score FLOAT,         -- 影响程度评分
    ai_analysis JSON,           -- AI分析结果
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 市场数据缓存表
CREATE TABLE market_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_type VARCHAR(50) NOT NULL, -- 'overview', 'sectors', 'news'
    data JSON NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 模拟交易记录表
CREATE TABLE simulated_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    action VARCHAR(10) NOT NULL, -- 'BUY', 'SELL'
    price FLOAT NOT NULL,
    quantity INTEGER NOT NULL,
    total_amount FLOAT NOT NULL,
    reason TEXT,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'executed', 'cancelled'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP NULL,
    FOREIGN KEY (stock_id) REFERENCES stocks(id)
);
```

---

## 🚀 分阶段实施计划

### Phase 1: 基础架构搭建 (第1-2周)

#### Week 1: 项目初始化
**目标**: 建立完整的开发环境和基础架构

**后端任务**:
- [ ] 创建项目目录结构
- [ ] 设置FastAPI应用框架
- [ ] 配置SQLite数据库和模型
- [ ] 实现基础API路由结构
- [ ] 配置环境变量和配置管理
- [ ] 建立日志系统

**前端任务**:
- [ ] 创建Vue.js 3项目
- [ ] 配置Vite构建工具
- [ ] 设置Element Plus UI框架
- [ ] 建立基础路由和页面结构
- [ ] 配置Axios HTTP客户端

**集成任务**:
- [ ] 建立前后端通信机制
- [ ] 实现基础的CORS配置
- [ ] 创建健康检查API

#### Week 2: 数据源集成
**目标**: 实现基础的数据获取和存储

**数据源开发**:
- [ ] 实现东方财富API客户端
- [ ] 实现腾讯财经API客户端
- [ ] 实现新浪财经API客户端（备用）
- [ ] 建立数据源容错机制
- [ ] 实现数据缓存策略

**核心功能**:
- [ ] 股票基础信息同步
- [ ] 实时行情数据获取
- [ ] 市场概览数据收集
- [ ] 板块数据聚合
- [ ] K线数据存储

**测试验证**:
- [ ] 单元测试覆盖数据源
- [ ] API接口测试
- [ ] 数据质量验证

### Phase 2: 因子引擎开发 (第3-4周)

#### Week 3: 因子计算引擎
**目标**: 实现多因子评分核心算法

**动量因子开发**:
```python
# momentum.py 核心因子
- calc_ma_score()      # 均线排列得分
- calc_rsi_score()     # RSI相对强弱指标
- calc_macd_score()    # MACD趋势指标
- calc_price_momentum() # 价格动量
- calc_volume_trend()  # 成交量趋势
```

**价值因子开发**:
```python
# value.py 价值因子
- calc_pe_percentile() # PE行业百分位
- calc_pb_percentile() # PB行业百分位
- calc_ps_score()      # 市销率评分
- calc_dividend_yield() # 股息率评分
```

**情绪因子开发**:
```python
# sentiment.py 情绪因子
- calc_turnover_score()    # 换手率异动
- calc_news_sentiment()    # 新闻情感得分
- calc_fund_flow_score()   # 资金流向得分
- calc_market_heat()       # 市场热度指标
```

**质量因子开发**:
```python
# quality.py 质量因子
- calc_roe_score()         # ROE稳定性得分
- calc_debt_ratio()        # 负债率健康度
- calc_revenue_growth()    # 营收增长质量
- calc_profit_consistency() # 盈利一致性
```

#### Week 4: 评分引擎与排名
**目标**: 实现综合评分和排名系统

**评分引擎**:
- [ ] 因子归一化算法
- [ ] 权重配置系统
- [ ] 综合评分计算
- [ ] 实时排名更新
- [ ] 历史评分存储

**调仓建议引擎**:
- [ ] 入池规则引擎
- [ ] 出池规则引擎
- [ ] 风控规则检查
- [ ] 建议生成逻辑
- [ ] 建议推送机制

### Phase 3: 前端界面开发 (第5-6周)

#### Week 5: 核心界面组件
**目标**: 实现主要用户界面

**市场监控仪表盘**:
- [ ] 市场情绪看板组件
- [ ] 板块热力图组件
- [ ] 实时数据更新机制
- [ ] 响应式布局设计

**股票列表组件**:
- [ ] 数据表格实现
- [ ] 排序和筛选功能
- [ ] 实时数据更新
- [ ] 行选择和详情联动

**图表组件**:
- [ ] ECharts集成
- [ ] K线图组件
- [ ] 技术指标叠加
- [ ] 交互功能实现

#### Week 6: 高级界面功能
**目标**: 完善用户交互体验

**股票池管理**:
- [ ] 股票池展示组件
- [ ] 调仓建议弹窗
- [ ] 确认/忽略操作
- [ ] 历史记录查看

**新闻分析界面**:
- [ ] 新闻流组件
- [ ] AI分析结果展示
- [ ] 关联股票高亮
- [ ] 情感分析可视化

**实时通知系统**:
- [ ] WebSocket客户端
- [ ] 实时消息推送
- [ ] 通知中心组件
- [ ] 消息状态管理

### Phase 4: AI集成与高级功能 (第7-8周)

#### Week 7: GLM-4.6集成
**目标**: 实现AI驱动的智能分析

**AI分析服务**:
- [ ] GLM-4.6 API客户端
- [ ] 新闻情感分析
- [ ] 事件影响评估
- [ ] 关联性分析
- [ ] 结构化输出处理

**智能推荐**:
- [ ] 基于AI的选股建议
- [ ] 风险提示生成
- [ ] 投资逻辑解释
- [ ] 个性化推荐

#### Week 8: 完善与优化
**目标**: 系统优化和测试

**性能优化**:
- [ ] 数据库查询优化
- [ ] 缓存策略优化
- [ ] 前端性能优化
- [ ] API响应时间优化

**测试与质量保证**:
- [ ] 单元测试覆盖
- [ ] 集成测试
- [ ] 用户界面测试
- [ ] 性能压力测试

**部署准备**:
- [ ] 生产环境配置
- [ ] 部署脚本编写
- [ ] 监控和日志配置
- [ ] 备份策略制定

---

## 🔧 关键技术实现细节

### 1. 多因子评分算法
```python
class ScoringEngine:
    def __init__(self):
        self.weights = {
            'momentum': 0.30,    # 动量因子权重
            'sentiment': 0.25,   # 情绪因子权重
            'value': 0.25,       # 价值因子权重
            'quality': 0.20      # 质量因子权重
        }

    def calculate_composite_score(self, stock_data):
        # 1. 计算各因子得分
        momentum_score = self.calc_momentum_factors(stock_data)
        sentiment_score = self.calc_sentiment_factors(stock_data)
        value_score = self.calc_value_factors(stock_data)
        quality_score = self.calc_quality_factors(stock_data)

        # 2. 归一化处理 (0-100分)
        normalized_scores = self.normalize_factors([
            momentum_score, sentiment_score, value_score, quality_score
        ])

        # 3. 加权求和
        composite_score = sum(
            score * self.weights[factor]
            for factor, score in zip(
                ['momentum', 'sentiment', 'value', 'quality'],
                normalized_scores
            )
        )

        return composite_score
```

### 2. WebSocket实时通信
```python
# 后端WebSocket处理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def broadcast_market_update(self, data: dict):
        for connection in self.active_connections:
            await connection.send_json({
                "type": "market_update",
                "data": data,
                "timestamp": datetime.now().isoformat()
            })

    async def send_suggestion(self, suggestion: dict):
        for connection in self.active_connections:
            await connection.send_json({
                "type": "pool_suggestion",
                "data": suggestion,
                "timestamp": datetime.now().isoformat()
            })
```

### 3. GLM-4.6新闻分析集成
```python
class GLM46Analyzer:
    def __init__(self, api_key: str):
        self.api_url = "https://open.bigmodel.cn/api/anthropic/v1/messages"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    async def analyze_news(self, news_title: str, news_content: str) -> dict:
        prompt = f"""
        分析以下财经新闻对A股市场的影响：
        标题：{news_title}
        内容：{news_content}

        请返回JSON格式的分析结果：
        {{
            "sentiment": "positive/negative/neutral",
            "related_sectors": ["板块1", "板块2"],
            "related_stocks": ["股票代码1", "股票代码2"],
            "impact_score": 0.0-1.0,
            "key_points": ["影响点1", "影响点2"]
        }}
        """

        # 调用GLM-4.6 API
        response = await self.call_glm46(prompt)
        return self.parse_response(response)
```

### 4. 前端响应式数据管理
```javascript
// Pinia Store - 市场数据管理
import { defineStore } from 'pinia'
import { socket } from '@/services/socket'

export const useMarketStore = defineStore('market', {
  state: () => ({
    overview: {},
    sectors: [],
    stocks: [],
    suggestions: [],
    isLoading: false
  }),

  actions: {
    initializeSocket() {
      socket.on('market_update', (data) => {
        this.overview = data.overview
        this.sectors = data.sectors
      })

      socket.on('pool_suggestion', (suggestion) => {
        this.suggestions.unshift(suggestion)
        this.showNotification(suggestion)
      })
    },

    async fetchMarketOverview() {
      this.isLoading = true
      try {
        const response = await api.get('/market/overview')
        this.overview = response.data
      } finally {
        this.isLoading = false
      }
    }
  }
})
```

---

## 📊 质量保证与测试策略

### 1. 代码质量标准
```yaml
代码规范:
  Python: PEP 8 + Black格式化
  JavaScript: ESLint + Prettier
  提交规范: Conventional Commits

测试覆盖率目标:
  单元测试: >= 80%
  集成测试: >= 70%
  E2E测试: 核心用户流程100%

性能指标:
  API响应时间: < 200ms (95%分位)
  页面加载时间: < 3秒
  实时数据延迟: < 500ms
```

### 2. 测试策略
```python
# 单元测试示例
import pytest
from app.services.scoring.engine import ScoringEngine

class TestScoringEngine:
    def test_momentum_factor_calculation(self):
        engine = ScoringEngine()
        test_data = {
            'prices': [10, 11, 12, 13, 14],
            'volumes': [1000, 1200, 1100, 1300, 1250]
        }
        score = engine.calc_momentum_score(test_data)
        assert 0 <= score <= 100

    def test_composite_score_range(self):
        engine = ScoringEngine()
        # 测试综合得分在合理范围内
        # ...更多测试用例
```

### 3. 部署检查清单
```yaml
环境检查:
  - [ ] Python 3.9+ 版本确认
  - [ ] Node.js 16+ 版本确认
  - [ ] GLM-4.6 API密钥配置
  - [ ] 数据库初始化脚本执行
  - [ ] 依赖包安装验证

功能验证:
  - [ ] 后端API健康检查
  - [ ] 前端页面加载正常
  - [ ] WebSocket连接稳定
  - [ ] 实时数据更新验证
  - [ ] 数据库读写测试

性能验证:
  - [ ] 内存使用监控
  - [ ] CPU使用率检查
  - [ ] 网络延迟测试
  - [ ] 数据库查询优化验证
```

---

## 🎯 成功指标与验收标准

### 技术指标
- **系统可用性**: >= 99%
- **数据准确性**: >= 99.5%
- **响应时间**: API < 200ms, 页面 < 3秒
- **并发用户**: 支持10个并发连接

### 业务指标
- **因子有效性**: 多因子评分与股票收益相关性 > 0.3
- **建议准确性**: 调仓建议胜率 > 60%
- **实时性**: 市场数据延迟 < 30秒
- **覆盖范围**: A股主要板块覆盖率 > 90%

### 用户体验指标
- **界面友好性**: 用户操作流程 <= 3步完成核心功能
- **数据可视化**: 关键信息一目了然
- **响应式设计**: 支持多种屏幕尺寸
- **错误处理**: 友好的错误提示和恢复机制

---

## 🔄 迭代与维护计划

### Phase 5: 优化迭代 (第9-12周)

**功能增强**:
- [ ] 更多技术指标集成
- [ ] 策略回测功能
- [ ] 风险管理模块
- [ ] 投资组合分析

**技术优化**:
- [ ] 微服务架构迁移
- [ ] 数据库性能优化
- [ ] 移动端适配
- [ ] 国际化支持

**运维改进**:
- [ ] 监控和告警系统
- [ ] 自动化部署流程
- [ ] 数据备份和恢复
- [ ] 性能监控仪表盘

---

## 📝 风险评估与应对策略

### 技术风险
| 风险项 | 影响程度 | 发生概率 | 应对策略 |
|--------|----------|----------|----------|
| 数据源API限制 | 高 | 中 | 多数据源备份，实现容错机制 |
| GLM-4.6 API限制 | 中 | 中 | 本地缓存，批量处理，成本控制 |
| 实时性能问题 | 中 | 低 | 异步处理，缓存优化，数据库调优 |
| 数据准确性 | 高 | 低 | 多源验证，异常检测，人工审核 |

### 业务风险
| 风险项 | 影响程度 | 发生概率 | 应对策略 |
|--------|----------|----------|----------|
| 因子模型失效 | 高 | 低 | 持续回测，模型调优，多因子分散 |
| 市场环境变化 | 中 | 中 | 动态权重调整，风险控制 |
| 监管政策变化 | 中 | 低 | 合规检查，政策跟踪 |

---

## 📚 文档与知识管理

### 技术文档
- [ ] API接口文档 (OpenAPI/Swagger)
- [ ] 数据库设计文档
- [ ] 部署运维文档
- [ ] 代码贡献指南

### 用户文档
- [ ] 用户使用手册
- [ ] 功能说明文档
- [ ] 常见问题解答
- [ ] 故障排除指南

### 开发文档
- [ ] 架构设计文档
- [ ] 算法说明文档
- [ ] 测试用例文档
- [ ] 版本发布说明

---

**这个实施计划为A股智能投顾助手项目提供了详细的技术路线图，涵盖了从架构设计到最终部署的完整流程。项目预计在8周内完成MVP版本，后续可根据使用情况进行功能增强和性能优化。**