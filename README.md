#!/usr/bin/env markdown

# A股智能投顾助手

[![CI](https://github.com/huangbolungit/QuantInit/actions/workflows/backend-ci.yml/badge.svg?branch=main)](https://github.com/huangbolungit/QuantInit/actions/workflows/backend-ci.yml)

> 基于多因子综合评分模型与 FastAPI + Vue3 的本地量化投顾工具，支持策略管理、信号生成、WebSocket 实时推送，并可选接入 GLM-4.6 做新闻情感与市场解读。

## 功能概览
- 实时市场数据与板块概览（Eastmoney/Tencent/Sina 兼容）
- 多因子评分（Momentum / Sentiment / Value / Quality 可配权重）
- 策略管理：创建、更新、删除与持久化（SQLite）
- 交易信号批量生成与查询（DB 优先，内存兜底）
- WebSocket `/ws/realtime` 实时交互（简单 ping/pong 与订阅确认）
- 前后端分离，提供 Docker 一键部署

## 项目结构
```
QuantInit/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── api/              # 路由（REST + WS）
│   │   ├── core/             # 配置/数据库
│   │   ├── models/           # SQLAlchemy 模型
│   │   └── services/         # 业务（因子/评分/回测/数据源/策略引擎）
│   ├── tests/                # 后端测试（pytest + httpx/starlette）
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                 # Vue3 + Vite 前端
│   ├── src/
│   ├── Dockerfile            # 构建静态资源，Nginx 托管
│   └── nginx.conf            # 反向代理到后端 /api 与 /ws
├── docker-compose.yml        # 一键启动前后端
└── .github/workflows/        # CI（后端+前端）
```

## 快速开始（本地开发）
### 准备环境
- Python 3.9+
- Node.js 16+（建议 20）

### 后端
```bash
cd backend
pip install -r requirements.txt
python main.py  # 或 uvicorn main:app --reload
```

### 前端
```bash
cd frontend
npm install
npm run dev
```

- 前端开发地址: http://localhost:5173
- 后端 API: http://localhost:8000
- 文档: http://localhost:8000/docs

## API 示例
创建策略
```bash
curl -s -X POST http://localhost:8000/api/strategies \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "demo-mr",
    "strategy_type": "mean_reversion",
    "parameters": {"lookback_period": 10, "buy_threshold": -0.05, "sell_threshold": 0.03},
    "stock_pool": ["000001", "000002"],
    "rebalance_frequency": 10
  }'
```

查询策略列表（分页/校验）
```bash
curl -s 'http://localhost:8000/api/strategies?limit=10&offset=0'
```

批量生成交易信号
```bash
curl -s -X POST http://localhost:8000/api/signals/generate
```

获取最新信号（DB 优先，内存兜底）
```bash
curl -s 'http://localhost:8000/api/signals/latest?limit=10&offset=0'
```

WebSocket ping/pong（浏览器示例）
```js
const ws = new WebSocket('ws://localhost:8000/ws/realtime');
ws.onopen = () => ws.send(JSON.stringify({ type: 'ping' }));
ws.onmessage = (e) => console.log('message:', e.data);
```

## Docker 一键运行
```bash
docker compose up --build -d
# 前端: http://localhost:5173
# 后端: http://localhost:8000 （API: /api, WS: /ws）
```
- 前端容器由 Nginx 提供静态资源，并已配置反向代理：
  - `/api/*` → `backend:8000/api/*`
  - `/ws/*`  → `backend:8000/ws/*`

停止与清理
```bash
docker compose down
```

## 测试
```bash
# 后端
cd backend
pytest -q

# 前端（如配置了测试）
cd frontend
npm test -- --run
```

## 配置
后端环境变量（`.env`，也可通过系统环境变量/CI 注入）：
```
DEBUG=True
HOST=127.0.0.1
PORT=8000
DATABASE_URL=sqlite+aiosqlite:///./data/database/stocks.db

# GLM-4.6（可选）
ANTHROPIC_AUTH_TOKEN=your_glm46_api_key_here
```

## 说明
- 默认使用 SQLite，本地首次运行会自动创建库/表。CI 中我们在测试前执行 Alembic 迁移以保证模型一致性。
- 为便于测试，若 DB 读取失败，部分接口会回退到内存数据，确保基本可用性。

## 许可与风险提示
本项目仅用于个人投资决策辅助，不构成任何投资建议。股市有风险，投资需谨慎。

