#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用配置管理
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    """应用设置"""

    # 基础配置
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"  # Changed to string for env compatibility

    # 服务器配置
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/database/stocks.db"

    # GLM-4.6 API配置
    ANTHROPIC_AUTH_TOKEN: Optional[str] = None
    GLM46_API_URL: str = "https://open.bigmodel.cn/api/anthropic/v1/messages"

    # 数据源配置
    EASTMONEY_API_BASE_URL: str = "http://push2.eastmoney.com"
    TENCENT_API_BASE_URL: str = "http://qt.gtimg.cn"
    SINA_API_BASE_URL: str = "http://hq.sinajs.cn"

    # 缓存配置
    CACHE_TTL: int = 300  # 5分钟
    REQUEST_TIMEOUT: int = 30

    # 因子权重配置
    MOMENTUM_WEIGHT: float = 0.30
    SENTIMENT_WEIGHT: float = 0.25
    VALUE_WEIGHT: float = 0.25
    QUALITY_WEIGHT: float = 0.20

    # 调仓阈值配置
    POOL_ENTRY_THRESHOLD: float = 90.0
    POOL_EXIT_THRESHOLD: float = 80.0
    MAX_POOL_SIZE: int = 20

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    # 开发模式
    DEVELOPMENT_MODE: bool = True

    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    @property
    def allowed_hosts_list(self) -> List[str]:
        """获取允许的主机列表"""
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",")]

    @property
    def factor_weights(self) -> dict:
        """获取因子权重配置"""
        return {
            'momentum': self.MOMENTUM_WEIGHT,
            'sentiment': self.SENTIMENT_WEIGHT,
            'value': self.VALUE_WEIGHT,
            'quality': self.QUALITY_WEIGHT
        }

    @property
    def is_glm46_configured(self) -> bool:
        """检查GLM-4.6是否已配置"""
        return bool(self.ANTHROPIC_AUTH_TOKEN and self.ANTHROPIC_AUTH_TOKEN != "your_glm46_api_key_here")


@lru_cache()
def get_settings() -> Settings:
    """获取设置实例（缓存）"""
    return Settings()


# 全局设置实例
settings = get_settings()
