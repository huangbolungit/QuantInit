# Windows 10 环境设置指南

## 🎯 系统要求

- **操作系统**: Windows 10/11
- **Python**: 3.9 或更高版本
- **Node.js**: 16 或更高版本
- **内存**: 至少 8GB RAM
- **存储**: 至少 2GB 可用空间

## 📦 安装依赖软件

### 1. 安装 Python
1. 访问 [Python官网](https://www.python.org/downloads/)
2. 下载最新的 Python 3.9+ 版本
3. 运行安装程序，**勾选 "Add Python to PATH"**
4. 验证安装：打开命令提示符，输入 `python --version`

### 2. 安装 Node.js
1. 访问 [Node.js官网](https://nodejs.org/)
2. 下载 LTS 版本
3. 运行安装程序，按默认设置安装
4. 验证安装：打开命令提示符，输入 `node --version`

## 🚀 快速开始

### 方法一：使用批处理文件（推荐）

1. **双击运行环境设置**
   ```
   双击 scripts\setup_windows.bat
   ```

2. **配置API密钥**
   - 编辑 `backend\.env` 文件
   - 将 `your_glm46_api_key_here` 替换为您的GLM-4.6 API密钥

3. **启动应用**
   ```
   双击 scripts\start_windows.bat
   ```

4. **访问应用**
   - 前端界面: http://localhost:5173
   - 后端API: http://localhost:8000
   - API文档: http://localhost:8000/docs

### 方法二：使用 PowerShell（推荐开发者）

1. **启用PowerShell脚本执行**
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
   ```

2. **运行环境设置**
   ```powershell
   .\scripts\setup_powershell.ps1
   ```

3. **配置API密钥**
   - 编辑 `backend\.env` 文件
   - 配置您的GLM-4.6 API密钥

4. **启动应用**
   ```powershell
   .\scripts\start_powershell.ps1
   ```

## 🔧 手动设置（高级用户）

### 设置后端

```batch
cd backend
python -m venv venv
venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
```

### 设置前端

```batch
cd frontend
npm install
```

### 启动服务

```batch
# 启动后端（新命令提示符窗口）
cd backend
venv\Scripts\activate.bat
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# 启动前端（另一个命令提示符窗口）
cd frontend
npm run dev
```

## 📁 可用脚本

| 脚本文件 | 功能 | 适用场景 |
|---------|------|----------|
| `setup_windows.bat` | 一键环境设置 | 新手推荐 |
| `start_windows.bat` | 启动完整应用 | 日常使用 |
| `dev_windows.bat` | 仅启动后端开发模式 | 后端开发 |
| `test_windows.bat` | 运行测试 | 测试验证 |
| `setup_powershell.ps1` | PowerShell环境设置 | PowerShell用户 |
| `start_powershell.ps1` | PowerShell启动应用 | PowerShell用户 |

## ⚙️ 配置说明

### 后端配置 (`backend\.env`)

```env
# GLM-4.6 API配置（必须）
ANTHROPIC_AUTH_TOKEN=your_glm46_api_key_here

# 数据库配置
DATABASE_URL=sqlite:///./data/database/stocks.db

# 应用配置
DEBUG=True
HOST=127.0.0.1
PORT=8000

# 因子权重配置
MOMENTUM_WEIGHT=0.30
SENTIMENT_WEIGHT=0.25
VALUE_WEIGHT=0.25
QUALITY_WEIGHT=0.20

# 调仓阈值配置
POOL_ENTRY_THRESHOLD=90
POOL_EXIT_THRESHOLD=80
MAX_POOL_SIZE=20
```

### 前端配置 (`frontend\.env`)

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_APP_TITLE=A股智能投顾助手
VITE_APP_VERSION=0.2.0-MVP
```

## 🔍 故障排除

### 常见问题

**1. Python不是内部或外部命令**
- 解决：重新安装Python，勾选"Add Python to PATH"
- 或手动添加Python到系统PATH环境变量

**2. pip命令不可用**
- 解决：确保虚拟环境已激活
- 运行 `python -m pip install --upgrade pip`

**3. Node.js命令不可用**
- 解决：重新安装Node.js，确保添加到PATH
- 重启命令提示符窗口

**4. 端口被占用**
- 解决：关闭占用端口的程序，或修改配置文件中的端口号
- 查找端口占用：`netstat -ano | findstr :8000`

**5. 权限问题**
- 解决：以管理员身份运行命令提示符
- 或修改PowerShell执行策略：`Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process`

### 检查清单

- [ ] Python 3.9+ 已安装并添加到PATH
- [ ] Node.js 16+ 已安装并添加到PATH
- [ ] GLM-4.6 API密钥已获取并配置
- [ ] 防火墙允许Python和Node.js网络访问
- [ ] 端口8000和5173未被占用
- [ ] 有足够的磁盘空间（至少2GB）

## 📞 获取帮助

1. **检查日志文件**
   - 后端日志：`backend\logs\app.log`
   - 前端控制台：浏览器开发者工具

2. **验证环境**
   ```batch
   python --version
   node --version
   npm --version
   pip --version
   ```

3. **测试网络连接**
   - 访问 http://localhost:8000/health
   - 检查API文档是否正常显示

4. **重新安装**
   - 删除 `backend\venv` 和 `frontend\node_modules`
   - 重新运行环境设置脚本

## 🎉 下一步

环境设置完成后，您可以：

1. **查看API文档** - http://localhost:8000/docs
2. **开始开发** - 修改代码实现自定义功能
3. **运行测试** - 使用 `test_windows.bat` 验证功能
4. **查看文档** - 阅读 `README.md` 了解更多功能

---

**提示**: 如果遇到问题，请先查看故障排除部分，然后检查控制台输出的错误信息。