#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket端点
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
import asyncio

router = APIRouter()

# 存储活跃连接
active_connections: List[WebSocket] = []


@router.websocket("/realtime")
async def websocket_endpoint(websocket: WebSocket):
    """实时数据推送"""
    await websocket.accept()
    active_connections.append(websocket)

    try:
        while True:
            # 等待客户端消息
            data = await websocket.receive_text()

            try:
                message = json.loads(data)

                # 处理不同类型的消息
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif message.get("type") == "subscribe":
                    # TODO: 实现订阅逻辑
                    await websocket.send_text(json.dumps({
                        "type": "subscription_ack",
                        "channel": message.get("channel")
                    }))
                else:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"Unknown message type: {message.get('type')}"
                    }))

            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))

    except WebSocketDisconnect:
        active_connections.remove(websocket)


async def broadcast_message(message: Dict[str, Any]):
    """向所有连接的客户端广播消息"""
    if active_connections:
        message_str = json.dumps(message)
        disconnected = []

        for connection in active_connections:
            try:
                await connection.send_text(message_str)
            except:
                disconnected.append(connection)

        # 移除断开的连接
        for connection in disconnected:
            if connection in active_connections:
                active_connections.remove(connection)