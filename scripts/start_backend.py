#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动后端服务
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """启动后端服务"""
    print("A股智能投顾助手 - 启动后端服务")
    print("=" * 50)

    # 检查是否在项目根目录
    backend_dir = Path("backend")
    if not backend_dir.exists():
        print("错误: 请在项目根目录运行此脚本")
        sys.exit(1)

    # 检查虚拟环境
    venv_dir = backend_dir / "venv"
    if not venv_dir.exists():
        print("错误: 未找到虚拟环境，请先运行 setup_powershell.ps1")
        sys.exit(1)

    # 检查环境变量文件
    env_file = backend_dir / ".env"
    if not env_file.exists():
        print("错误: 未找到.env文件，请先运行 setup_powershell.ps1")
        sys.exit(1)

    print("[OK] 环境检查通过")
    print("[START] 启动后端服务...")
    print("[URL] 服务地址: http://localhost:8000")
    print("[DOCS] API文档: http://localhost:8000/docs")
    print("[HEALTH] 健康检查: http://localhost:8000/health")
    print()
    print("按 Ctrl+C 停止服务")
    print("-" * 50)

    try:
        # 使用虚拟环境中的Python启动服务
        python_exe = venv_dir / "Scripts" / "python.exe"

        # 验证Python可执行文件存在
        if not python_exe.exists():
            print(f"错误: 未找到Python可执行文件: {python_exe}")
            print(f"当前目录: {Path.cwd()}")
            print(f"虚拟环境目录: {venv_dir}")
            print(f"Python文件路径: {python_exe}")
            sys.exit(1)

        print(f"[OK] 找到Python: {python_exe}")
        print(f"[DIR] 工作目录: {backend_dir}")

        # 在后端目录中启动服务
        subprocess.run([str(python_exe), "main.py"], check=True, cwd=backend_dir)
    except KeyboardInterrupt:
        print("\n[STOP] 服务已停止")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] 服务启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()