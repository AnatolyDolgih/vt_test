from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from collections import deque
from pydantic import BaseModel
from datetime import datetime
from typing import Deque, Dict, Any

import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.websockets import WebSocketDisconnect
import uvicorn
from typing import Dict

import logging
import os
import uvicorn
import asyncio

class ItemModel(BaseModel):
    topic: str

THEME = ""
flag_theme = False

PATH_TO_LOG = "./logs/server/"
LOG_FILE = f"server_logs_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

class ColorFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    blue = "\x1b[36;20m"
    
    FORMATS = {
        logging.DEBUG: grey,
        logging.INFO: blue,
        logging.WARNING: yellow,
        logging.ERROR: red,
        logging.CRITICAL: bold_red
    }
    
    def format(self, record):
        color = self.FORMATS.get(record.levelno)
        message = super().format(record)
        if color:
            message = color + message + self.reset
        return message

os.makedirs(PATH_TO_LOG, exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Console output
console_handler = logging.StreamHandler()
console_handler.setFormatter(ColorFormatter(
    "[%(asctime)s] %(levelname)s: %(message)s"
))

# File output 
file_handler = logging.FileHandler(
    os.path.join(PATH_TO_LOG, LOG_FILE),
    encoding = "utf-8"
)
file_handler.setFormatter(logging.Formatter(
    "[%(asctime)s] %(levelname)s: %(message)s"
))

logger.addHandler(console_handler)
logger.addHandler(file_handler)

app = FastAPI(title="BICA project")
active_connections: Dict[str, WebSocket] = {}

is_processing_done = True

@app.get("/is_processing_done")
def is_processing_done():
	global is_processing_done
	return {"done" : is_processing_done}

# Вебсокеты для передачи информации о записи звука
@app.websocket("/wss/{client_type}")
async def websocket_endpoint(websocket: WebSocket, client_type: str):
    await websocket.accept()
    active_connections[client_type] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Message from {client_type}: {data}")
            global is_processing_done 
            if(data == "recording_started"):
                is_processing_done = False
            else:
                is_processing_done = True
    except WebSocketDisconnect:
        active_connections.pop(client_type, None)

async def send_command(client_type: str, command: str):
    if client_type in active_connections:
        await active_connections[client_type].send_text(command)
        return True
    return False

@app.post("/start_recording")
async def start_recording():
    success = await send_command("local", "start_recording")
    return {"status": "success" if success else "client offline"}

@app.post("/stop_recording")
async def stop_recording():
    success = await send_command("local", "stop_recording")
    return {"status": "success" if success else "client offline"}


app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

data_queue: Deque[Dict[str, Any]] = deque(maxlen=100)  
lock = asyncio.Lock()  

@app.get("/")
async def read_index():
    return FileResponse("static/select_theme.html")


@app.post("/set_theme")
def set_theme(item: ItemModel):
    global THEME
    global flag_theme
    THEME = item.topic
    flag_theme = True
    return {"theme": "theme is successfully installed"}
    
@app.get("/get_theme")
def get_theme():
    print(THEME)
    return {"theme": THEME}
    
    
@app.get("/get_theme_to_bica")
def get_theme():
	return {"theme": THEME}


@app.get("/essay_editor")
async def editor():
    return FileResponse("static/index.html")


@app.post("/essay_data/")
async def receive_essay(request: Request):
    try:
        data = await request.json()
        
        # Валидация данных
        if not isinstance(data.get("text"), str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid text format"
            )
        
        async with lock:
            essay = {
                "text": data["text"],
                "language": data.get("language", "en"),
                "timestamp": datetime.utcnow().isoformat(),
                "ip": request.client.host
            }
            data_queue.append(essay)
            logger.info(essay)
            logger.info(f"Essay received. Queue size: {len(data_queue)}")
        
        return {"status": "success"}
    
    except Exception as e:
        logger.error(f"Error receiving essay: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
        

@app.get("/get_data/")
async def get_essay():
    try:
        async with lock:
            if not data_queue:
                return {
                    "status": "empty",
                    "message": "No essays in queue"
                }
            
            essay = data_queue.popleft()
            logger.info(f"Essay dispatched. Remaining: {len(data_queue)}")
            
            return {
                "status": "success",
                "data": essay,
                "remaining": len(data_queue)
            }
    
    except Exception as e:
        logger.error(f"Error getting essay: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)


# ==== Chat storage (server-side) ====
from pydantic import BaseModel
from typing import List

class ChatMessage(BaseModel):
    role: str
    text: str
    ts: int

CHAT_DB: List[ChatMessage] = []

@app.get("/chat/messages")
def get_chat_messages() -> List[ChatMessage]:
    return CHAT_DB

@app.post("/chat/messages")
def post_chat_message(msg: ChatMessage):
    CHAT_DB.append(msg)
    return {"ok": True, "count": len(CHAT_DB)}
