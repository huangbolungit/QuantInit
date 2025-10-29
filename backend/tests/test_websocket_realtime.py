import json
from starlette.testclient import TestClient

from main import app


def test_websocket_ping_pong():
    with TestClient(app) as client:
        with client.websocket_connect("/ws/realtime") as ws:
            ws.send_text(json.dumps({"type": "ping"}))
            msg = ws.receive_json()
            assert msg.get("type") == "pong"

