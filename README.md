# A股智能投顾助手

基于多因子综合评分模型的本地量化投顾工具，集成GLM-4.6 AI分析，为个人投资决策提供专业支持。

## 🎯 项目概述

**版本**: v0.2-MVP
**更新时间**: 2025年10月18日
**技术栈**: FastAPI + Vue.js 3 + SQLite + GLM-4.6

### 核心功能
- 📊 实时市场监控仪表盘
- 📰 AI驱动的新闻情感分析
- 🏆 动态智能股票池管理
- 📈 专业K线图表分析
- 🔔 实时调仓建议推送

## 🏗️ 项目结构

```
stock-advisor/
├── backend/          # FastAPI后端服务
│   ├── app/
│   │   ├── api/      # API路由
│   │   ├── core/     # 核心配置
│   │   ├── models/   # 数据模型
│   │   ├── services/ # 业务逻辑
│   │   └── utils/    # 工具函数
│   ├── data/         # 数据存储
│   └── tests/        # 后端测试
├── frontend/         # Vue.js前端应用
│   ├── src/
│   │   ├── components/ # 组件
│   │   ├── views/      # 页面
│   │   ├── services/   # API服务
│   │   └── stores/     # 状态管理
│   └── public/        # 静态资源
├── docs/             # 项目文档
├── scripts/          # 部署脚本
└── README.md
```

## 🚀 快速开始

### 环境要求
- Python 3.9+
- Node.js 16+
- npm/yarn

### 后端设置
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # 配置API密钥
uvicorn main:app --reload
```

### 前端设置
```bash
cd frontend
npm install
npm run dev
```

### 访问应用
- 前端界面: http://localhost:5173
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

## 🔧 配置说明

### 环境变量配置 (.env)
```env
# GLM-4.6 API配置
ANTHROPIC_AUTH_TOKEN=your_glm46_api_key_here

# 数据库配置
DATABASE_URL=sqlite:///./data/database/stocks.db

# 应用配置
DEBUG=True
SECRET_KEY=your_secret_key_here
```

### API密钥获取
1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/)
2. 注册并获取API密钥
3. 配置到环境变量中

## 📊 核心功能说明

### 多因子评分引擎
- **动量因子** (30%): 均线排列、RSI、MACD
- **情绪因子** (25%): 新闻情感、资金流向、换手率
- **价值因子** (25%): PE/PB百分位、市销率、股息率
- **质量因子** (20%): ROE稳定性、负债率、盈利一致性

### 实时数据源
- 东方财富API (主要)
- 腾讯财经API (备用)
- 新浪财经API (补充)

### AI智能分析
- GLM-4.6大模型集成
- 新闻情感分析
- 市场影响评估
- 关联性分析

## 🛠️ 开发指南

### 添加新的因子
1. 在 `backend/app/services/factors/` 创建新文件
2. 实现因子计算函数
3. 在评分引擎中注册新因子
4. 更新前端显示逻辑

### 添加新的数据源
1. 在 `backend/app/services/data_sources/` 创建客户端
2. 实现标准化的数据获取接口
3. 添加到数据源管理器
4. 更新配置文件

## 📈 性能指标

- API响应时间: < 200ms (95%分位)
- 页面加载时间: < 3秒
- 实时数据延迟: < 500ms
- 系统可用性: > 99%

## 🧪 测试

```bash
# 后端测试
cd backend
pytest

# 前端测试
cd frontend
npm run test
```

## 📚 文档

- [API文档](docs/api/)
- [部署文档](docs/deployment/)
- [开发文档](docs/development/)

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目仅用于个人投资决策辅助，不构成投资建议。

## ⚠️ 风险提示

股市有风险，投资需谨慎。本系统提供的分析仅供参考，请根据自身风险承受能力做出投资决策。

---

**开发团队**: 个人开发项目
**技术支持**: 基于[实施计划](implementation_plan.md)构建
[![CI](https://github.com/huangbolungit/QuantInit/actions/workflows/backend-ci.yml/badge.svg?branch=main)](https://github.com/huangbolungit/QuantInit/actions/workflows/backend-ci.yml)
