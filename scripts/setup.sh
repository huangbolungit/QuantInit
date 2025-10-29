#!/bin/bash

# A股智能投顾助手 - 环境设置脚本

echo "🚀 开始设置A股智能投顾助手开发环境..."

# 检查Python版本
echo "📋 检查Python版本..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3未安装，请先安装Python 3.9或更高版本"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python版本: $PYTHON_VERSION"

# 检查Node.js版本
echo "📋 检查Node.js版本..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js未安装，请先安装Node.js 16或更高版本"
    exit 1
fi

NODE_VERSION=$(node -v)
echo "✅ Node.js版本: $NODE_VERSION"

# 设置后端环境
echo "🔧 设置后端环境..."
cd backend

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建Python虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔄 激活虚拟环境..."
source venv/bin/activate

# 升级pip
echo "⬆️ 升级pip..."
pip install --upgrade pip

# 安装依赖
echo "📦 安装Python依赖..."
pip install -r requirements.txt

# 创建环境变量文件
if [ ! -f ".env" ]; then
    echo "📝 创建环境变量文件..."
    cp .env.example .env
    echo "⚠️  请编辑 backend/.env 文件，配置您的API密钥"
fi

# 创建数据目录
mkdir -p data/database
mkdir -p logs

# 返回根目录
cd ..

# 设置前端环境
echo "🔧 设置前端环境..."
cd frontend

# 安装依赖
echo "📦 安装Node.js依赖..."
npm install

# 创建环境变量文件
if [ ! -f ".env" ]; then
    echo "📝 创建前端环境变量文件..."
    cat > .env << EOF
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_APP_TITLE=A股智能投顾助手
VITE_APP_VERSION=0.2.0-MVP
EOF
fi

# 返回根目录
cd ..

# 创建启动脚本
echo "📝 创建启动脚本..."
cat > start.sh << 'EOF'
#!/bin/bash

# A股智能投顾助手启动脚本

echo "🚀 启动A股智能投顾助手..."

# 检查环境变量配置
if [ ! -f "backend/.env" ]; then
    echo "❌ 后端环境变量文件不存在，请先运行 setup.sh"
    exit 1
fi

# 启动后端
echo "🔧 启动后端服务..."
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动前端
echo "🎨 启动前端服务..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo "✅ 服务启动完成！"
echo "📱 前端地址: http://localhost:5173"
echo "📊 后端API: http://localhost:8000"
echo "📖 API文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待用户中断
trap "echo '🛑 停止服务...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
EOF

chmod +x start.sh

# 创建开发脚本
echo "📝 创建开发脚本..."
cat > dev.sh << 'EOF'
#!/bin/bash

# 开发模式启动脚本

# 启动后端开发服务器
echo "🔧 启动后端开发服务器..."
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000 &
EOF

chmod +x dev.sh

# 创建测试脚本
echo "📝 创建测试脚本..."
cat > test.sh << 'EOF'
#!/bin/bash

# 测试脚本

echo "🧪 运行后端测试..."
cd backend
source venv/bin/activate
pytest

echo "🧪 运行前端测试..."
cd ../frontend
npm run test
EOF

chmod +x test.sh

# 创建部署脚本
echo "📝 创建部署脚本..."
cat > deploy.sh << 'EOF'
#!/bin/bash

# 部署脚本

echo "🏗️ 构建前端..."
cd frontend
npm run build

echo "📦 准备后端..."
cd ../backend
source venv/bin/activate

echo "🚀 启动生产服务器..."
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
EOF

chmod +x deploy.sh

echo ""
echo "🎉 环境设置完成！"
echo ""
echo "📋 下一步操作："
echo "1. 编辑 backend/.env 文件，配置您的GLM-4.6 API密钥"
echo "2. 运行 ./start.sh 启动应用"
echo "3. 访问 http://localhost:5173 查看应用"
echo ""
echo "🔧 其他脚本："
echo "- ./dev.sh: 开发模式启动"
echo "- ./test.sh: 运行测试"
echo "- ./deploy.sh: 生产部署"
echo ""
echo "📚 更多信息请查看 README.md"