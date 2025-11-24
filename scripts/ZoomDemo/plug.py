import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
import logging
import time
from contextlib import asynccontextmanager

#логика при запуске
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код, выполняемый при запуске
    print("Starting up...")
    # для того чтобы сделать кнопку зеленой при запуске
    while True:
        try:
            re = requests.post(url="http://127.0.0.1:8532/start", json={})
            break
        except:
            pass
        
    yield
    # Код, выполняемый при завершении
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)
username = "player"

@app.get("/")
async def root():
    return {"message": "Hello World"}

class TextItem(BaseModel):
    text: str

@app.post("/start")
def dialogue_start(item: TextItem):
    username = item.text
    print(username)

    #реквест послать эмоции, bot: 1 вторая женщина bot: 0 первая
    re_emo = requests.post(url="http://127.0.0.1:8532/emotions", json={"bot":1, "emotions": {"Happy": 1, "Sad": 0, 
                                                            "Disgust": 0, "Angry": 1, 
                                                            "Surprise": 0, "Fear": 0}})
    re_emo = requests.post(url="http://127.0.0.1:8532/emotions", json={"bot":0, "emotions": {"Happy": 0, "Sad": 1, 
                                                            "Disgust": 1, "Angry": 0, 
                                                            "Surprise": 1, "Fear": 1}})
    #реквест послать файл чтобы они сказали, "direction": "bot" смотрят друг на друга, "direction": "player" смотрят в камеру, "bot":1 первая женщина "bot":2 вторая
    re = requests.post(url="http://127.0.0.1:8532/talk", json={"address": os.path.abspath("test_audio.wav"), "direction": "bot", "bot":2})
    time.sleep(4)
    re = requests.post(url="http://127.0.0.1:8532/talk", json={"address": os.path.abspath("test_audio.wav"), "direction": "bot", "bot":1})
    time.sleep(4)
    re = requests.post(url="http://127.0.0.1:8532/talk", json={"address": os.path.abspath("test_audio.wav"), "direction": "player", "bot":2})

    

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=5000)