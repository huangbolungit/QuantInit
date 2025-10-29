#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断脚本 - 检查项目环境和依赖
"""

import sys
import os
import importlib
from pathlib import Path

def check_python_version():
    """检查Python版本"""
    print("🐍 Python版本检查...")
    version = sys.version_info
    print(f"当前版本: {version.major}.{version.minor}.{version.micro}")

    if version.major == 3 and version.minor >= 9:
        print("✅ Python版本符合要求 (>=3.9)")
        return True
    else:
        print("❌ Python版本过低，需要3.9或更高版本")
        return False

def check_dependencies():
    """检查依赖包"""
    print("\n📦 检查依赖包...")

    required_packages = [
        'fastapi',
        'uvicorn',
        'sqlalchemy',
        'httpx',
        'pandas',
        'numpy',
        'pydantic',
        'pydantic_settings',
        'python_dotenv',
        'loguru'
    ]

    missing_packages = []

    for package in required_packages:
        try:
            if package == 'pydantic_settings':
                importlib.import_module('pydantic_settings')
            else:
                importlib.import_module(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - 未安装")
            missing_packages.append(package)

    return len(missing_packages) == 0, missing_packages

def check_project_structure():
    """检查项目结构"""
    print("\n📁 检查项目结构...")

    base_dir = Path(__file__).parent
    required_dirs = [
        'app',
        'app/api',
        'app/api/endpoints',
        'app/core',
        'app/models',
        'app/services',
        'data',
        'tests'
    ]

    required_files = [
        'requirements.txt',
        '.env.example',
        'main.py'
    ]

    missing_items = []

    # 检查目录
    for dir_path in required_dirs:
        full_path = base_dir / dir_path
        if full_path.exists():
            print(f"✅ {dir_path}/")
        else:
            print(f"❌ {dir_path}/ - 缺失")
            missing_items.append(str(full_path))

    # 检查文件
    for file_path in required_files:
        full_path = base_dir / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - 缺失")
            missing_items.append(str(full_path))

    return len(missing_items) == 0, missing_items

def check_env_file():
    """检查环境变量文件"""
    print("\n🔧 检查环境配置...")

    env_file = Path('.env')
    env_example = Path('.env.example')

    if not env_file.exists():
        if env_example.exists():
            print("⚠️  .env文件不存在，但找到.env.example")
            print("💡 建议复制.env.example到.env并配置API密钥")
        else:
            print("❌ .env和.env.example都不存在")
        return False

    # 检查关键配置
    try:
        from dotenv import load_dotenv
        load_dotenv()

        anthropic_token = os.getenv('ANTHROPIC_AUTH_TOKEN')
        if anthropic_token and anthropic_token != 'your_glm46_api_key_here':
            print("✅ GLM-4.6 API密钥已配置")
            return True
        else:
            print("⚠️  GLM-4.6 API密钥未配置或使用默认值")
            return False
    except Exception as e:
        print(f"❌ 环境变量加载失败: {e}")
        return False

def main():
    """主函数"""
    # 设置控制台编码
    if sys.platform == 'win32':
        import subprocess
        subprocess.run(['chcp', '65001'], shell=True)

    print("A股智能投顾助手 - 环境诊断")
    print("=" * 50)

    # 检查Python版本
    python_ok = check_python_version()

    # 检查依赖
    deps_ok, missing_deps = check_dependencies()

    # 检查项目结构
    struct_ok, missing_struct = check_project_structure()

    # 检查环境配置
    env_ok = check_env_file()

    print("\n" + "=" * 50)
    print("📊 诊断结果:")

    if python_ok and deps_ok and struct_ok:
        print("🎉 项目结构完整，可以启动应用")

        if not env_ok:
            print("\n⚠️  启动前请注意:")
            print("1. 配置.env文件中的GLM-4.6 API密钥")
            print("2. 确保数据库目录有写入权限")

        print("\n🚀 启动命令:")
        print("python main.py")
    else:
        print("❌ 发现问题，需要修复:")

        if not python_ok:
            print("- 升级Python到3.9+版本")

        if not deps_ok:
            print(f"- 安装缺失的依赖: {', '.join(missing_deps)}")
            print("  运行: pip install -r requirements.txt")

        if not struct_ok:
            print("- 项目结构不完整，请检查缺失的文件/目录")

    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()