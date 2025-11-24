import asyncio
import aiohttp
import websockets
from fastapi import FastAPI
import uvicorn
from pydantic import BaseModel
import logging
import pyaudio
import wave
from pathlib import Path
import os
import numpy as np
import requests

DEVICE_ID = 33
FORMAT_VAD = pyaudio.paInt16  
CHANNELS_VAD = 1           
RATE_VAD = 48000
FRAME_DURATION_VAD = 30       
FRAME_SIZE_VAD = int(RATE_VAD * FRAME_DURATION_VAD / 1000)  
SILENCE_THRESHOLD = 50     

OUTPUT_DIR = Path(os.getenv("PATH_TO_AUDIO", "recordings"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LocalServer")

FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 48000
CHUNK = 1024

app = FastAPI()
app.locked = False

# Глобальный экземпляр PyAudio для избежания утечек ресурсов
_global_audio = None

def get_global_audio():
    global _global_audio
    if _global_audio is None:
        _global_audio = pyaudio.PyAudio()
    return _global_audio

def getCorrectAudioDevice(deviceName: str, defaultSampleRate: float) -> int:
    audio = get_global_audio()
    deviceID = -1
    for i in range(audio.get_device_count()):
        info = audio.get_device_info_by_index(i)
        if deviceName in info['name'] and defaultSampleRate == info['defaultSampleRate']:
            return info['index']
    return deviceID

class AudioRecorder:
    def __init__(self):
        self.audio = get_global_audio()  # Используем глобальный экземпляр
        self.stream = None
        self.recording = False
        self.frames = []
        self.session = None
        self.count = 0
        self.device_id = getCorrectAudioDevice("CABLE Output (VB-Audio Virtual Cable)", 48000.0)
        logger.info(f"Initialized with device ID: {self.device_id}")

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()
        # Останавливаем запись при выходе
        if self.recording:
            await self.stop_recording()

    async def async_post_request(self, url: str, json_data: dict):
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.post(url, json=json_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"POST request failed with status {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error in POST request: {e}")
            return None

    def start_recording(self):
        if self.recording:
            logger.warning("Already recording")
            return
            
        logger.info("Starting recording...")
        self.recording = True
        self.frames = []
        try:
            self.stream = self.audio.open(
                format=FORMAT_VAD,
                channels=CHANNELS_VAD,
                rate=RATE_VAD,  # Используем константу RATE_VAD вместо 48000
                input=True,
                #input_device_index=self.device_id,
                frames_per_buffer=FRAME_SIZE_VAD
            )
            logger.info("Stream opened successfully")
        except Exception as e:
            logger.error(f"Failed to start stream: {e}")
            self.recording = False
            self.stream = None

    async def stop_recording(self, filename="test"):
        if not self.recording:
            logger.warning("Not recording, nothing to stop")
            return
            
        logger.info("Stop recording")
        self.recording = False
        
        # Сохраняем ссылку на frames до закрытия потока
        frames_to_save = self.frames.copy()
        self.frames = []
        
        # ЗАКРЫВАЕМ ПОТОК СРАЗУ при остановке записи
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            except Exception as e:
                logger.error(f"Error closing stream: {e}")

        filepath = os.path.abspath(os.path.join(OUTPUT_DIR, f"{filename}_{self.count}.wav"))
        self.count += 1

        # Сохраняем файл только если есть данные
        if len(frames_to_save) > 0:
            try:
                with wave.open(str(filepath), 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(RATE_VAD)
                    wf.writeframes(b''.join(frames_to_save))
                
                print(f"frames: {len(frames_to_save)}")
                if len(frames_to_save) > 10:
                    lock()
                    print("post request to http://127.0.0.1:5000/stt_zoom")
                    response = await self.async_post_request(
                        "http://127.0.0.1:5000/stt_zoom",
                        {"file": str(filepath)}
                    )
                    if response:
                        logger.info(f"Server response: {response}")
                else:
                    print("not enough frames! recording not sent")
            except Exception as e:
                logger.error(f"Error saving file: {e}")
        else:
            print("no frames recorded")
        
        logger.info(f"Recording saved as {filepath}")

async def audio_capture():
    """Захват аудио с улучшенной обработкой ошибок"""
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    while True:
        try:
            # Проверяем, должна ли идти запись и есть ли поток
            should_record = (recorder.recording and 
                           hasattr(recorder, 'stream') and 
                           recorder.stream is not None)
            
            if should_record:
                try:
                    # Проверяем активность потока
                    is_active = recorder.stream.is_active()
                except OSError as e:
                    logger.warning(f"Stream error: {e}")
                    recorder.recording = False
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error("Too many consecutive errors, resetting recorder state")
                        recorder.recording = False
                        if recorder.stream:
                            try:
                                recorder.stream.close()
                            except:
                                pass
                            recorder.stream = None
                        consecutive_errors = 0
                    await asyncio.sleep(0.1)
                    continue
                
                if is_active:
                    try:
                        # Читаем данные
                        frame = recorder.stream.read(FRAME_SIZE_VAD, exception_on_overflow=False)
                        
                        # Обрабатываем аудио данные
                        audio_data = np.frombuffer(frame, dtype=np.int16)
                        
                        if CHANNELS_VAD == 2:
                            audio_data = audio_data.reshape(-1, 2).mean(axis=1).astype(np.int16)
                        
                        frame = audio_data.tobytes()
                        recorder.frames.append(frame)
                        
                        consecutive_errors = 0  # Сбрасываем счетчик ошибок при успешном чтении
                        
                    except Exception as e:
                        logger.error(f"Read error: {e}")
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            logger.error("Too many read errors, stopping recording")
                            recorder.recording = False
                else:
                    logger.warning("Stream is not active but recording flag is True")
                    recorder.recording = False
                    consecutive_errors += 1
            else:
                consecutive_errors = 0  # Сбрасываем счетчик когда не записываем
                
            # Всегда небольшая задержка для избежания busy waiting
            await asyncio.sleep(0.001)  # Уменьшил задержку для более отзывчивой остановки
                
        except Exception as e:
            logger.error(f"Unexpected error in audio_capture: {e}")
            consecutive_errors += 1
            await asyncio.sleep(0.1)  # Большая задержка при критических ошибках

recorder = AudioRecorder()

async def websocket_client():
    """WebSocket клиент с улучшенной обработкой переподключения"""
    reconnect_delay = 5
    max_reconnect_delay = 60
    
    while True:
        try:
            async with websockets.connect("wss://bica-project.tw1.ru/wss/local") as ws:
                logger.info("Connected to remote server")
                reconnect_delay = 5  # Сбрасываем задержку при успешном подключении
                
                while True:
                    try:
                        message = await ws.recv()
                        if message == "start_recording":
                            recorder.start_recording()
                            await ws.send("recording_started")
                        elif message == "stop_recording":
                            await recorder.stop_recording()
                            await ws.send("recording_stopped")
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning("WebSocket connection closed")
                        break
                        
        except Exception as e:
            logger.error(f"WebSocket error: {e}, reconnecting in {reconnect_delay}s...")
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)  # Exponential backoff

@app.post("/start_recording")
def start_from_post_request():
    if not app.locked:
        logger.info("Starting recording via POST request")
        recorder.start_recording()
    else:
        logger.warning("Server is locked, cannot start recording")

@app.post("/unlock")
def unlock():
    logger.info("Server unlocked")
    app.locked = False

@app.post("/lock")
def lock():
    logger.info("Server locked")
    app.locked = True

@app.post("/stop_recording")
async def stop_from_post_request():
    if not app.locked:
        logger.info("Stopping recording via POST request")
        await recorder.stop_recording()
    else:
        logger.warning("Server is locked, cannot stop recording")

@app.on_event("startup")
async def startup():
    asyncio.create_task(audio_capture())
    asyncio.create_task(websocket_client())

@app.on_event("shutdown")
async def shutdown():
    """Корректное завершение работы"""
    global _global_audio
    if recorder.recording:
        await recorder.stop_recording()
    if _global_audio:
        _global_audio.terminate()
        _global_audio = None

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=7777)