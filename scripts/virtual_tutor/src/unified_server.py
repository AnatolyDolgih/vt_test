from __future__ import annotations

import asyncio
import logging
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Dict, List

from fastapi import Body, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
NEW_UI_DIR = BASE_DIR / "new_ui" / "static"
LEGACY_UI_DIR = BASE_DIR / "ui"
LOG_DIR = BASE_DIR / "logs" / "server"

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / f"server_logs_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Unified Virtual Tutor Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


theme: str = ""
active_connections: Dict[str, WebSocket] = {}
legacy_connections: Dict[str, WebSocket] = {}
is_processing_done: bool = True


data_queue: Deque[Dict[str, Any]] = deque(maxlen=100)
lock = asyncio.Lock()


class ItemModel(BaseModel):
    topic: str


class EssayPayload(BaseModel):
    text: str
    language: str | None = "en"


class ChatMessage(BaseModel):
    role: str
    text: str
    ts: int


class LegacyMessage(BaseModel):
    type: str
    content: str
    timestamp: str


CHAT_DB: List[ChatMessage] = []


@app.get("/")
async def read_index():
    if (NEW_UI_DIR / "select_theme.html").exists():
        return FileResponse(NEW_UI_DIR / "select_theme.html")
    return {"message": "Virtual Tutor server is running"}


@app.get("/essay_editor")
async def essay_editor():
    return FileResponse(NEW_UI_DIR / "index.html")


@app.get("/is_processing_done")
def is_processing_done_status():
    return {"done": is_processing_done}


@app.websocket("/wss/{client_type}")
async def websocket_endpoint(websocket: WebSocket, client_type: str):
    await websocket.accept()
    active_connections[client_type] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug("WS message from %s: %s", client_type, data)
            global is_processing_done
            if data == "recording_started":
                is_processing_done = False
            else:
                is_processing_done = True
    except WebSocketDisconnect:
        active_connections.pop(client_type, None)


async def send_command(client_type: str, command: str) -> bool:
    if client_type in active_connections:
        await active_connections[client_type].send_text(command)
        return True
    return False


@app.post("/start_recording")
async def start_recording():
    global is_processing_done
    is_processing_done = False
    success = await send_command("local", "start_recording")
    return {"status": "success" if success else "client offline"}


@app.post("/stop_recording")
async def stop_recording():
    global is_processing_done
    is_processing_done = True
    success = await send_command("local", "stop_recording")
    return {"status": "success" if success else "client offline"}


@app.post("/set_theme")
def set_theme(item: ItemModel):
    global theme
    theme = item.topic
    return {"theme": "theme is successfully installed"}


@app.get("/get_theme")
def get_theme():
    return {"theme": theme}


@app.get("/get_theme_to_bica")
def get_theme_to_bica():
    return {"theme": theme}


@app.post("/essay_data/")
async def receive_essay(payload: EssayPayload, request: Request):
    try:
        async with lock:
            essay = {
                "text": payload.text,
                "language": payload.language or "en",
                "timestamp": datetime.utcnow().isoformat(),
                "ip": request.client.host if request.client else "unknown",
            }
            data_queue.append(essay)
            logger.info("Essay received. Queue size: %s", len(data_queue))
        return {"status": "success"}
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error receiving essay: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@app.get("/get_data/")
async def get_essay():
    try:
        async with lock:
            if not data_queue:
                return {"status": "empty", "message": "No essays in queue"}
            essay = data_queue.popleft()
        logger.info("Essay dispatched. Remaining: %s", len(data_queue))
        return {"status": "success", "data": essay, "remaining": len(data_queue)}
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error getting essay: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@app.get("/chat/messages")
def get_chat_messages() -> List[ChatMessage]:
    return CHAT_DB


@app.post("/chat/messages")
def post_chat_message(msg: ChatMessage):
    CHAT_DB.append(msg)
    return {"ok": True, "count": len(CHAT_DB)}


@app.websocket("/legacy/wss/{client_id}")
async def legacy_websocket(websocket: WebSocket, client_id: str):
    await websocket.accept()
    legacy_connections[client_id] = websocket
    try:
        while True:
            text = await websocket.receive_text()
            msg = LegacyMessage.model_validate_json(text)
            logger.info("Legacy message from %s: %s", client_id, msg.content)
            reply = msg.model_copy(update={"content": f"Tutor: {msg.content}"})
            await websocket.send_json(reply.model_dump())
    except WebSocketDisconnect:
        legacy_connections.pop(client_id, None)


app.mount("/new", StaticFiles(directory=NEW_UI_DIR, html=True), name="new_ui_static")
app.mount("/static", StaticFiles(directory=NEW_UI_DIR, html=True), name="new_ui_legacy_path")
app.mount("/legacy", StaticFiles(directory=LEGACY_UI_DIR, html=True), name="legacy_ui_static")


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5050)
