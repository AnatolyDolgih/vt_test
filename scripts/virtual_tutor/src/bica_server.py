from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Body
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, TypeAdapter
from pydantic.tools import parse_obj_as
from server.virtual_tutor import VirtualTutor, VirtualAgentPrototype
import server.helper as hlp
import uvicorn
import json
import argparse
import aiohttp
import time
import os
from contextlib import asynccontextmanager

def show_time(text):
    cur_time = time.perf_counter()
    hours, rem = divmod(cur_time, 3600)
    min, rem = divmod(rem, 60)
    sec, ms = divmod(rem, 1)
    ms = int(ms*1000)
    print(f"{text}: {int(hours):02}:{int(min):02}:{int(sec):02}:{ms:03}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    timeout = aiohttp.ClientTimeout(total=120)
    connector = aiohttp.TCPConnector(limit=100, limit_per_host=100)
    app.state.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
    #app.state.vt_list2 = {} # создание списка одного агента (один инстанс на каждого клиента)
    app.state.vt_list = {} # создание списка инстансов другого агента (один инстанс на каждого клиента)
    app.state.vt_prototype = []
    app.state.vt_prototype.append(VirtualAgentPrototype(hlp.start_prompt_moral_5, "gpt-4o-mini-tts", "nova"))
    app.state.vt_prototype.append(VirtualAgentPrototype(hlp.start_prompt_moral_6, "gpt-4o-mini-tts", "alloy"))
    yield
    await app.state.session.close()

app = FastAPI(lifespan=lifespan)

# убираем кэширование файлов, а то плохо выходит
class StaticFilesWithoutCaching(StaticFiles):
    def is_not_modified(self, *args, **kwargs) -> bool:
        return False

class WssItem(BaseModel):
    type: str
    content: str
    timestamp: str

class PostItem(BaseModel):
    input : str | None = None
    direction : str | None = None
    actor_id : int | None = None

class EssayItem(BaseModel):
    NewestText : str | None = None
    FullText : str | None = None


class VizItem(BaseModel):
    input_text: str

class TTSItem(BaseModel):
    input_text: str
    actor_id: int

@app.get("/")
def process_root():
    print("Hello!", flush=True)
    return {"message" : "Hello, worl2d!!!"}

'''
@app.post("/getAnswerDialog")
async def process_post_viz1(request: Request, item: VizItem):
    viz_vt = request.app.state.viz_vt
    viz_vt.logger_dialog.info(f"User (viz):{item.input_text}")
    answer = await viz_vt.generate_answer(item.input_text)
    viz_vt.logger_dialog.info(f"Tutor (viz): {answer}")
    return {"answer_text": answer, 
            "emotion": 3}


@app.post("/getAnswerEssay")
async def process_post_viz2(request: Request, item: VizItem):
    viz_vt = request.app.state.viz_vt
    viz_vt.logger_essay.info(f"Get part essay: {item.input_text}")
    answer = await viz_vt.generate_answer(item.input_text)
    viz_vt.logger_essay.info(f"Tutor answer: {answer}")
    return {"answer_text": answer}
    '''


class ConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

manager = ConnectionManager()

@app.websocket("/test_1/wss/{client_id}")
async def websocket_endpoint_3(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    bicaServerSession = websocket.app.state.session
    try:
        virtual_tutor = VirtualTutor(client_id, hlp.start_prompt_moral_5, bicaServerSession)
        while True:
            data = await websocket.receive_text()
            data_dict = json.loads(data)
            data_model = TypeAdapter(WssItem).validate_python(data_dict)
            actor_replic = await virtual_tutor.generate_answer(data_model.content)
            data_model.content = actor_replic
            await manager.send_personal_message(data_model.model_dump(), websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.websocket("/test_2/wss/{client_id}")
async def websocket_endpoint_4(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    bicaServerSession = websocket.app.state.session
    try:
        virtual_tutor = VirtualTutor(client_id, hlp.start_prompt_moral_5, bicaServerSession)
        while True:
            data = await websocket.receive_text()
            data_dict = json.loads(data)
            data_model = TypeAdapter(WssItem).validate_python(data_dict)
            actor_replic = await virtual_tutor.generate_answer(data_model.content)
            data_model.content = actor_replic
            await manager.send_personal_message(data_model.model_dump(), websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/test/{client_id}/getAnswer")
async def process_post(request: Request, client_id: int, item: PostItem):
    show_time("Get request")
    print("i'm here")
    vt_list = request.app.state.vt_list
    if not client_id in vt_list.keys():
        vt_list_to_append = []
        for agent_prototype in (request.app.state.vt_prototype):
            vt_list_to_append.append(VirtualTutor(client_id, 
                                                  agent_prototype.start_msg, 
                                                  request.app.state.session, 
                                                  agent_prototype.model, 
                                                  agent_prototype.voice))
        vt_list[client_id] = vt_list_to_append
    print(f"item.input: {item.input}")
    print(f"type: {type(item.input)}")
    show_time("Start req to OpenAI")
    answer = await vt_list[client_id][item.actor_id].generate_answer(item.input, TTS = True)
    print ("generating with TTS")
    show_time("End req to OpenAI")
    print (f"TTS: {os.path.abspath(answer.get('TTS'))}")
    emotions = answer.get('Emotions')
    print("emotions: ", emotions)
    return {
            "Desk": "",
            "Reply": answer.get('Reply'),
            #"Short": answer.get('Short'), 
            "Direction": "player",
            "Happy": emotions[0],
            "Sad": emotions[1],
            "Surprise": emotions[2],
            "Disgust": emotions[3],
            "Angry": emotions[4],
            "Afraid": emotions[5],
            "TTS": os.path.abspath(answer.get('TTS'))
        }

@app.post("/test/{client_id}/getTTS")
async def process_post_TTS(request: Request, client_id: int, item: TTSItem):
    show_time("Get request")
    print("i'm here")
    vt_list = request.app.state.vt_list
    print("prttp")
    print(request.app.state.vt_prototype)
    print("prttp")
    print(vt_list.keys())
    if not client_id in vt_list.keys():
        vt_list_to_append = []
        for agent_prototype in (request.app.state.vt_prototype):
            vt_list_to_append.append(VirtualTutor(client_id, 
                                                  agent_prototype.start_msg, 
                                                  request.app.state.session, 
                                                  agent_prototype.model, 
                                                  agent_prototype.voice))
        print(f"list to append:{vt_list_to_append}")
        vt_list[client_id] = vt_list_to_append
    print (vt_list)
    print (vt_list[client_id])
    print(f"item.input tts: {item.input_text}")
    show_time("Start req to OpenAI")
    answer = await vt_list[client_id][item.actor_id].generate_TTS(item.input_text)
    print ("generating with TTS getTTS")
    show_time("End req to OpenAI")
    print (f"TTS: {os.path.abspath(answer.get('TTS'))}")
    
    return {
            "TTS": os.path.abspath(answer.get('TTS'))
        }


@app.post("/test/{client_id}/setTheme")
async def set_theme(request: Request, client_id: int, theme: str = Body(..., media_type="text/plain")):
    vt_list = request.app.state.vt_list
    start_prompt = "Discussion topic: " + theme
    print(theme)
    vt_list_to_append = []
    for agent_prototype in (request.app.state.vt_prototype):
        vt_list_to_append.append(VirtualTutor(client_id, 
                                                start_prompt + theme + agent_prototype.start_msg, 
                                                request.app.state.session, 
                                                agent_prototype.model, 
                                                agent_prototype.voice))
        print(f"list to append:{vt_list_to_append}")
    vt_list[client_id] = vt_list_to_append
    return

@app.post("/test/{client_id}/sendEssay")
async def process_post_2(request: Request, client_id: int, item: EssayItem):
    vt_list = request.app.state.vt_list
    vt_list2 = request.app.state.vt_list2
    if not client_id in vt_list.keys():
        vt_list_to_append = []
        for agent_prototype in (request.app.state.vt_prototype):
            vt_list_to_append.append(VirtualTutor(client_id, 
                                                  agent_prototype.start_msg, 
                                                  request.app.state.session, 
                                                  agent_prototype.model, 
                                                  agent_prototype.voice))
        vt_list[client_id] = vt_list_to_append

    vt_list[client_id][item.actor_id].logger_essay.info(f"User new (viz): {item.NewestText}")
    vt_list[client_id][item.actor_id].logger_essay.info(f"User full (viz): {item.FullText}")  
    answer = await vt_list2[client_id][item.actor_id].generate_answer(item.NewestText, TTS = True)
    vt_list[client_id][item.actor_id].logger_essay.info(f"Tutor: {answer}")
    return {
            "Desk": "",
            "Reply": answer,
            "Direction": "player",
            "Happy": 1,
            "Sad": 0.1,
            "Surprise": 0.1,
            "Disgust": 0,
            "Angry": 0,
            "Afraid": 0,
            "TTS": os.path.abspath(answer.get('TTS'))
        }

# Обработка зпросов от визуализации
# TODO: разобраться с маршрутами!!!

app.mount("/test_1", StaticFilesWithoutCaching(directory="./ui_moral_1", html=True), name="static")
app.mount("/test_2", StaticFilesWithoutCaching(directory="./ui_moral_2", html=True), name="static")

# TODO:
# сделать нормальные параметры запуска:
# -a, --address - адрес запуска
# -p, --port - номер порта
# -h, --help - помощь
# -v, --version - версия программы

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", action="store_true", 
        dest="local", help="запуск сервера локально")
    
    args = parser.parse_args()
        
    host_ip = "0.0.0.0"
    if args.local:
        host_ip="127.0.0.1" 
    print("I'm started")
    uvicorn.run("bica_server:app", host=host_ip, port=5050, reload=True)
