import uvicorn
import whisper
from fastapi import FastAPI
from pydantic import BaseModel
import requests
import torch
import uuid
import os
from pathlib import Path
import logging
import time
import wave
import asyncio
import contextlib
from contextlib import asynccontextmanager
import datetime
import random
import librosa 
import psutil
import soundfile as sf
from pydub import AudioSegment
from pydub.playback import play

#логика при запуске
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код, выполняемый при запуске
    print("Starting up...")
    st_logger.info(f"Starting up123")
    app.speech_time_left = 0.0
    # инициализация!!
    
    while True:
        try:
            re = requests.post(url="http://127.0.0.1:8532/start", json={})
            break
        except:
            pass
        
    print("запощено")
    yield
    # Код, выполняемый при завершении
    print("Shutting down...")
    st_logger.info(f"Shutting down123")

app = FastAPI(lifespan=lifespan)
username = "player"

@app.get("/")
async def root():
    return {"message": "Hello World"}


# Настройка логирования
logging.basicConfig(
    #encoding="utf-8",
    level=logging.DEBUG, 
    format="%(asctime)s:  %(levelname)s:  %(message)s",
    handlers=[
        logging.FileHandler("st_server_audio.log", encoding="utf-8"),
        logging.StreamHandler()
    ])
st_logger = logging.getLogger(__name__)

class WavItem(BaseModel):
    file: str | None = None

class TextItem(BaseModel):
    text: str


@app.post("/start")
def dialogue_start(item: TextItem):

    username = item.text
    app.speech_time_left = 0.0
    # инициализация!!
    #re_content = requests.post(url="http://127.0.0.1:8532/text", json={"text": "1. Open the website on your phone. \n 2. Locate the green “Talk” button, ignore everything else on the site. Do not tap the button!  \n 3. IMPORTANT: get to the microphone that is connected to Zoom.  \n 4. Before you start talking to the microphone, press and hold the button.  \n 5. When you finish your utterance, release the button. \n  6. Wait for AI to answer before you press the button again."})
    
    re = requests.post(url="http://127.0.0.1:7777/lock", json={})
    text = "What do you think about AGI and its future?"
    re = requests.post(url="http://127.0.0.1:5050/test/4/getTTS", json={"input_text": text, "actor_id" : 1})
    file_path = re.json()["TTS"]
    print(file_path)
    re = requests.post(url="http://127.0.0.1:8532/talk", json={"address": file_path, "direction": "bot", "bot":2})
    speech_begin_time = time.time()
    st_logger.info(f"end of synthesize speech")
    
    
    #st_logger.info(f"request to server bica")
    #re = requests.post(url="http://127.0.0.1:5050/test/4/getAnswer", json={"input": "result", "direction" : None})
    total_lines_amount = 1 # сколько реплик будет сказано в начальном диалоге ВСЕГО

    for i in range (total_lines_amount):
        
        st_logger.info(f"request to server bica")
        if i == total_lines_amount-1:
            re = requests.post(url="http://127.0.0.1:5050/test/4/getAnswer", json={"input": text + "###It's time to move on to the next phase of the discussion! Summarize and ask the audience what they think!.###", "direction" : None, "actor_id":i%2})
        
        elif i == total_lines_amount-2:
            re = requests.post(url="http://127.0.0.1:5050/test/4/getAnswer", json={"input": text + "###It will soon be time to move on to the next phase of the discussion! Summarize your previous points and politely tell your opponent to ask the audience what they think!.###", "direction" : None, "actor_id":i%2})
        
        else:
            print("Starting up1...")
            re = requests.post(url="http://127.0.0.1:5050/test/4/getAnswer", json={"input": text, "direction" : None, "actor_id":i%2})
        
        print("Starting up10...")

        duration = get_wav_duration_pydub(file_path)

        
        st_logger.info(f"get answer from server bica")

        st_logger.info(f"json: {str(re.json())}")

        text = str(re.json()['Reply'])
        print ("emotions [posted: ]", re.json()['Happy'])
        re_emo = requests.post(url="http://127.0.0.1:8532/emotions", json={"bot":i%2, "emotions": {"Happy": re.json()['Happy'], "Sad": re.json()['Sad'], 
                                                              "Disgust": re.json()['Disgust'], "Angry": re.json()['Angry'], 
                                                              "Surprise": re.json()['Surprise'], "Fear": re.json()['Afraid']}})
        print (re_emo)
        #content = str(re.json()['Short'])
        file_path = str(re.json()['TTS'])
        '''
        if i%2 == 0:
            tts_model.tts_to_file(text=text.replace("AGI", "Ay Gee I"), file_path=file_path)
        else:
            tts_model2.tts_to_file(text=text.replace("AGI", "Ay Gee I"), file_path=file_path)
            pitch_down(file_path)
        '''
        if (time.time() - speech_begin_time < (duration+0.2)):
            time.sleep(duration+0.2 - (time.time() - speech_begin_time))
            print(time.time() - speech_begin_time)
        if i == total_lines_amount - 1:
            re = requests.post(url="http://127.0.0.1:8532/talk", json={"address": file_path, "direction": "Player", "bot": i%2+1, "joy": 1})
        else:
            re = requests.post(url="http://127.0.0.1:8532/talk", json={"address": file_path, "direction": "bot", "bot": i%2+1, "joy": 1})
        speech_begin_time = time.time()
        print(f"{re.text} actor id {i%2}")
    re = requests.post(url="http://127.0.0.1:7777/unlock", json={})
    


device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"device: {device}")

whisper_model = whisper.load_model("tiny.en", device=device)


@app.post("/stt_zoom")
def transcribe_stt(item: WavItem):
    st_logger.info(f"start transcribing stt zoom: {item.file}")
    #print(f"start transcribing: {item.file}")
    
    result = whisper_model.transcribe(item.file, language="en", fp16=True)
    result = result['text']
    ################################################
    # audio = whisper.load_audio(item.file)
    # audio = whisper.pad_or_trim(audio)
    # mel = whisper.log_mel_spectrogram(audio).to(whisper_model.device)
    # options = whisper.DecodingOptions(language="en", fp16=True)
    # result = whisper.decode(whisper_model, mel, options)
    
    app.speech_time_left = 0.0
    file_id = str(uuid.uuid4()) # генерация уникального айди файла, в который будут записываться все результаты STT
    file_path = os.path.abspath(os.path.join(OUTPUT_DIR, f"output_{file_id}.wav")) 
    
    text = result
    print("STT result:", result)
    if text is None or text == ' ' or text == '':
        text = "Sorry, I couldn't hear you!"
        re_emo = requests.post(url="http://127.0.0.1:8532/emotions", json={"bot":0, "emotions": {"Happy": 0, "Sad": 1, 
                                                              "Disgust": 0, "Angry": 0, 
                                                              "Surprise": 0, "Fear": 0}})
        re_emo = requests.post(url="http://127.0.0.1:8532/emotions", json={"bot":1, "emotions": {"Happy": 0, "Sad": 1, 
                                                              "Disgust": 0, "Angry": 0, 
                                                              "Surprise": 0, "Fear": 0}})
        re = requests.post(url="http://127.0.0.1:5050/test/4/getTTS", json={"input_text": text, "actor_id" : 1})
        file_path = re.json()["TTS"]
        print(file_path)
        re = requests.post(url="http://127.0.0.1:8532/talk", json={"address": file_path, "direction": "", "bot":2})
        re = requests.post(url="http://127.0.0.1:7777/unlock", json={})
        return()
    if "good bye" in text.lower() or "goodbye" in text.lower():

        '''text = "Goodbye!"
        re = requests.post(url="http://127.0.0.1:5050/test/4/getTTS", json={"input_text": text, "actor_id" : 1})
        file_path = re.json()["TTS"]
        print(file_path)
        re = requests.post(url="http://127.0.0.1:8532/talk", json={"address": file_path, "direction": "", "bot":2})'''

        print("closing!")
        close_process_by_name("Classroom_actual.exe", force_kill=True)
        # Get the directory where your script is located
        script_dir = os.path.dirname(__file__)
        # Go up one level and navigate to the test.txt file
        file_path = os.path.join(script_dir, "..", "..", "test.txt")
        # Normalize the path
        file_path = os.path.normpath(file_path)

        with open(file_path, 'r') as file:
            line = file.readline().strip()
            values = list(map(int, line.split()))
            
        print("Values:", values)
        
        kill_process_tree(values[0])
        kill_process_tree(values[1])
        kill_process_tree(values[2])
        kill_process_tree(values[4])
        kill_process_tree(values[3])
    speech_begin_time = time.time()

    total_lines_amount = 2*int(round(2*random.random()))

    probability_conversation = random.random()

    print(probability_conversation)
    print (total_lines_amount)
    if total_lines_amount > 1:
        for i in range (total_lines_amount):
            
            print("checkpoint_achieved")
            st_logger.info(f"request to server bica")
            if i == total_lines_amount-1:
                re = requests.post(url="http://127.0.0.1:5050/test/4/getAnswer", json={"input": text + "###It's time to move on to the next phase of the discussion! Ask the audience what they think!.###", "direction" : None, "actor_id":i%2})
            
            #elif i == total_lines_amount-2:
                #re = requests.post(url="http://127.0.0.1:5050/test/4/getAnswer", json={"input": text + "###It will soon be time to move on to the next phase of the discussion! Politely tell your opponent to ask the audience what they think!.###", "direction" : None, "actor_id":i%2})
            
            else:
                re = requests.post(url="http://127.0.0.1:5050/test/4/getAnswer", json={"input": text, "direction" : None, "actor_id":i%2})
            
            if os.path.exists(file_path):
                duration = get_wav_duration_pydub(file_path)
            else:
                duration = 0.0

            st_logger.info(f"get answer from server bica")
            

            st_logger.info(f"json: {str(re.json())}")

            text = str(re.json()['Reply'])
            
            file_path = str(re.json()['TTS'])
            re_emo = requests.post(url="http://127.0.0.1:8532/emotions", json={"bot":i%2, "emotions": {"Happy": re.json()['Happy'], "Sad": re.json()['Sad'], 
                                                              "Disgust": re.json()['Disgust'], "Angry": re.json()['Angry'], 
                                                              "Surprise": re.json()['Surprise'], "Fear": re.json()['Afraid']}})
            print (re_emo)
            st_logger.info(f"start synthesize speech1111111111111111111")

            print(duration+0.2 - (time.time() - speech_begin_time))

            if (time.time() - speech_begin_time < (duration+0.2)):
                time.sleep(duration+0.2 - (time.time() - speech_begin_time))
                
            if i == total_lines_amount-1 or i == 0:
                re = requests.post(url="http://127.0.0.1:8532/talk", json={"address": file_path, "direction": "Player", "bot": i%2+1, "joy": 1})
            else:
                re = requests.post(url="http://127.0.0.1:8532/talk", json={"address": file_path, "direction": "bot", "bot": i%2+1, "joy": 1})

            speech_begin_time = time.time()
            print(f"{re.text} actor id {i%2}")
        re = requests.post(url="http://127.0.0.1:7777/unlock", json={})
    elif probability_conversation > 0.5:
        print("checkpoint_achieved1")
        re = requests.post(url="http://127.0.0.1:5050/test/4/getAnswer", json={"input": text, "direction" : None, "actor_id":0})
        st_logger.info(f"get answer from server bica")

        st_logger.info(f"json: {str(re.json())}")

        text = str(re.json()['Reply'])
        
        file_path = str(re.json()['TTS'])

        re_emo = requests.post(url="http://127.0.0.1:8532/emotions", json={"bot":0, "emotions": {"Happy": re.json()['Happy'], "Sad": re.json()['Sad'], 
                                                              "Disgust": re.json()['Disgust'], "Angry": re.json()['Angry'], 
                                                              "Surprise": re.json()['Surprise'], "Fear": re.json()['Afraid']}})
        print (re_emo)

        re = requests.post(url="http://127.0.0.1:8532/talk", json={"address": file_path, "direction": "Player", "bot": 1, "joy": 1})
        re = requests.post(url="http://127.0.0.1:7777/unlock", json={})
    else:
        print("checkpoint_achieved2")
        re = requests.post(url="http://127.0.0.1:5050/test/4/getAnswer", json={"input": text, "direction" : None, "actor_id":1})
        re_emo = requests.post(url="http://127.0.0.1:8532/emotions", json={"bot":1, "emotions": {"Happy": re.json()['Happy'], "Sad": re.json()['Sad'], 
                                                              "Disgust": re.json()['Disgust'], "Angry": re.json()['Angry'], 
                                                              "Surprise": re.json()['Surprise'], "Fear": re.json()['Afraid']}})
        st_logger.info(f"get answer from server bica")

        st_logger.info(f"json: {str(re.json())}")
        
        text = str(re.json()['Reply'])
        
        file_path = str(re.json()['TTS'])
        #tts_model2.tts_to_file(text=text.replace("AGI", "Ay Gee I"), file_path=file_path)
        re = requests.post(url="http://127.0.0.1:8532/talk", json={"address": file_path, "direction": "Player", "bot": 2, "joy": 1})
        re = requests.post(url="http://127.0.0.1:7777/unlock", json={})
    re = requests.post(url="http://127.0.0.1:7777/unlock", json={})

@app.post("/on_get_essay")
def get_essay(item:TextItem):
    re = requests.post(url="http://127.0.0.1:7777/lock", json={})
    st_logger.info(f"request to server bica")
    if item.text == "":
        return 
    re = requests.post(url="http://127.0.0.1:5050/test/4/getAnswer", json={"input": item.text, "direction" : None, "actor_id": 0})
    re2 = requests.post(url="http://127.0.0.1:5050/test/4/getAnswer", json={"input": item.text, "direction" : None, "actor_id": 1})

    print ("emotions [posted: ]", re.json()['Happy'])
    re_emo = requests.post(url="http://127.0.0.1:8532/emotions", json={"bot":0, "emotions": {"Happy": re.json()['Happy'], "Sad": re.json()['Sad'], 
                                                              "Disgust": re.json()['Disgust'], "Angry": re.json()['Angry'], 
                                                              "Surprise": re.json()['Surprise'], "Fear": re.json()['Afraid']}})
    print (re_emo)

    st_logger.info(f"get answer from server bica")
    text = str(re.json()['Reply'])
    text2 = str(re2.json()['Reply'])
    file_id = str(uuid.uuid4())
    file_path = os.path.abspath(os.path.join(OUTPUT_DIR, f"output_{file_id}.wav"))
    file_path2 = os.path.abspath(os.path.join(OUTPUT_DIR, f"output2_{file_id}.wav"))
    
    file_path = str(re.json()['TTS'])
    
    file_path2 = str(re2.json()['TTS'])
    
    re = requests.post(url="http://127.0.0.1:8532/talk", json={"address": file_path})
    print(f"{re.text}")
    
    duration = get_wav_duration_pydub(file_path)

    time.sleep(duration)

    re = requests.post(url="http://127.0.0.1:8532/talk", json={"address": file_path2, "direction": "bot", "bot":1})

    duration = get_wav_duration_pydub(file_path)

    time.sleep(duration) 
    re = requests.post(url="http://127.0.0.1:7777/unlock", json={})


def pitch_down (file_path: str):
    sound = AudioSegment.from_file(file_path, format="wav")
    
    # Define the desired pitch shift in octaves (e.g., 0.5 for half an octave up)
    octaves = -0.2

    # Calculate the new sample rate based on the pitch shift
    new_sample_rate = int(sound.frame_rate * (2.0 ** octaves))

    # Create a new sound object with the adjusted sample rate
    lowpitch_sound = sound._spawn(sound.raw_data, overrides={'frame_rate': new_sample_rate})

    velocidad_X = 1.2 # No puede estar por debajo de 1.0
    lowpitch_sound = lowpitch_sound.speedup(velocidad_X, 150, 25)
    # Convert to a standard sample rate (e.g., 44.1kHz) for compatibility
    lowpitch_sound = lowpitch_sound.set_frame_rate(44100)


    
    # Export the pitch-shifted sound to a new WAV file
    lowpitch_sound.export(file_path, format="wav")

def kill_process_tree(pid):
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        
        # Kill children first
        for child in children:
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        
        # Kill parent
        parent.kill()
        print(f"Successfully killed process tree for PID {pid}")
        
    except psutil.NoSuchProcess:
        print(f"Process with PID {pid} not found")
    except Exception as e:
        print(f"Error killing process tree: {e}")

def close_process_by_name(process_name, force_kill=False, timeout=5):
    """Close all processes with the given name and their child processes
    
    Args:
        process_name: Name of the process to terminate
        force_kill: If True, use kill() after terminate() if process doesn't exit
        timeout: Time to wait for graceful termination before force killing
    """
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == process_name:
            try:
                # Get all child processes recursively
                children = proc.children(recursive=True)
                all_processes = [proc] + children
                
                # Terminate all processes (children first is handled by recursive)
                for process in all_processes:
                    try:
                        process.terminate()
                    except psutil.NoSuchProcess:
                        pass  # Process already terminated
                    except psutil.AccessDenied:
                        print(f"Access denied to terminate: {process.name()} (PID: {process.pid})")
                
                # Wait for processes to terminate gracefully
                if force_kill:
                    gone, alive = psutil.wait_procs(all_processes, timeout=timeout)
                    
                    # Force kill any processes that didn't terminate
                    for process in alive:
                        try:
                            process.kill()
                            print(f"Force killed: {process.name()} (PID: {process.pid})")
                        except psutil.NoSuchProcess:
                            pass
                        except psutil.AccessDenied:
                            print(f"Access denied to force kill: {process.name()} (PID: {process.pid})")
                
                print(f"Terminated process tree: {process_name} (PID: {proc.info['pid']}) with {len(children)} children")
                
            except psutil.NoSuchProcess:
                print(f"Process already terminated: {process_name}")
            except psutil.AccessDenied:
                print(f"Access denied to terminate: {process_name}")

def get_wav_duration_pydub(filename):
    audio = AudioSegment.from_wav(filename)
    duration = len(audio) / 1000.0  # Convert milliseconds to seconds
    return duration

if __name__ == "__main__":
    OUTPUT_DIR = Path(os.getenv("PATH_TO_AUDIO", "synthesize"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"device is used: {device}")
    uvicorn.run(app, host="localhost", port=5000)
    #test_transcribe()