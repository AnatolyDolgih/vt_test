import numpy as np
from . import helper as hlp
import logging
from pathlib import Path
import os
from .base_moral_scheme import BaseMoralScheme
from .oai_interface import Interface
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
root=os.getenv("ROOT")

script_path = Path(__file__).absolute()
project_root = script_path.parent.parent.parent
print(project_root)

root = str(project_root)
if not root:
    raise ValueError("Не задана переменная ROOT")

def create_logger(logger_name, log_dir, log_file):
    Path(log_dir).mkdir(parents=True, exist_ok=True)    
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(os.path.join(log_dir, log_file), mode='w', encoding='utf-8')
    formatter = logging.Formatter("%(asctime)s | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

class VirtualAgentPrototype:
    def __init__(self, start_msg, model, voice):
        self.start_msg = start_msg
        self.model = model
        self.voice = voice
'''
class DummyVirtualTutor:
    def __init__(self, id, start_msg, session):
        self.client_session = session
        self.client_id = id
        self.messages = [ {"role": "system", "content": start_msg} ]
        self.oai_interface = Interface(self.client_session)
        now = datetime.now()
        time_string = now.strftime("%Y-%m-%d-%H-%M-%S")
        self.logger_dialog = create_logger(f"dialog_logger_{self.client_id}", f"{root}/logs_dummy/{self.client_id}", f"dialog_{time_string}.log")
        self.logger_essay = create_logger(f"essay_logger_{self.client_id}", f"{root}/logs_dummy/{self.client_id}", f"essay_{time_string}.log")
        
        self.logger_dialog.info("This is dialog log")
        self.logger_essay.info("This is essay log")
        
    async def generate_answer(self, replic):
        self.messages.append({"role": "user", "content": replic})
        tutor_response = await self.oai_interface.get_dummy_replic(self.messages)
        return tutor_response'''

class VirtualTutor:
    def __init__(self, m_id, start_msg, session, model = 'tts-1', voice = 'nova'):
        self.client_session = session
        self.client_id = m_id
        now = datetime.now()
        time_string = now.strftime("%Y-%m-%d-%H-%M-%S")
        self.logger_dialog = create_logger(f"dialog_logger_{self.client_id}", f"{root}/logs_moral/{self.client_id}", f"dialog_{time_string}.log")
        self.logger_essay = create_logger(f"essay_logger_{self.client_id}", f"{root}/logs_moral/{self.client_id}", f"essay_{time_string}.log")

        self.logger_dialog.info("This is dialog log")
        self.logger_essay.info("This is essay log")
        # голос и модель для tts
        self.model = model
        self.voice = voice
        # список моральных схем
        self.ms_list = [BaseMoralScheme(base_intentions=hlp.first_space, 
                                        session=self.client_session,
                                        changed_message=hlp.from1to2, 
                                        feelings=hlp.feelings1), 
                        BaseMoralScheme(base_intentions=hlp.second_space, 
                                        session=self.client_session,
                                        changed_message=hlp.from2to3, 
                                        feelings=hlp.feelings2), 
                        BaseMoralScheme(base_intentions=hlp.third_space,
                                        session=self.client_session,
                                        changed_message=hlp.from3to4, 
                                        feelings=hlp.feelings3),
                        BaseMoralScheme(base_intentions=hlp.third_space, 
                                        session=self.client_session, 
                                        feelings=hlp.feelings4,)]
        
        self.last_replic = ""
        self.prev_moral_id = 0
        self.cur_moral_id = 0
        self.messages = [ {"role": "assistant", "content": start_msg} ]
        self.schemes = [False, False, False, False]
        self.brain = [False, False, False, False]

    async def generate_TTS(self, message):
        TTS_path = await self.ms_list[self.cur_moral_id].oai_interface.get_tts(model=self.model, voice=self.voice, input=message) # генерируем голос если надо
        print(f"результат ттс generate_tts:{TTS_path}")
        return {
            "TTS": TTS_path
        }

    def get_positive_base_intentions(self):
        dictionary = self.ms_list[self.cur_moral_id].get_base_intentions()
        list = []
        for i in range (1, 5):
            list.append(dictionary[i])
        return list
            
    def feelings_to_emotions(self):
        feelings = self.ms_list[self.cur_moral_id].get_feelings()
        positive = feelings[:4]      
        negative = feelings[4:]    
        print("pos: ", positive)
        print("neg: ", negative)
       
        positive_intents = self.get_positive_base_intentions()
        print("pints: ", positive_intents)
        result = [positive[i] - negative[i] for i in range(4)]
        print("sultre: ", result)
        emotions = [0, 0, 0, 0, 0, 0]
        for i in range (4):
            emotions = [emotions[j] + result[i]*hlp.feelings_to_emotions[positive_intents[i]][j] for j in range (6)]
            print(emotions)
        for i in range (6):
            emotions[i] = emotions[i] * 5
            if emotions[i] < 0:
                emotions[i] = 0
            if emotions[i] > 1:
                emotions[i] = 1
            print ("done")
            print(emotions)
        print ("final")
        print(emotions)
        return emotions

    async def generate_answer(self, replic, TTS = False,):
        self.logger_dialog.warning(f'Сх: {self.schemes}') #Выводим состояние моральных схем
        self.logger_dialog.warning(f'Br: {self.brain}') #Выводим состояние моральных схем

        intents = self.ms_list[self.cur_moral_id].get_base_intentions()
        self.logger_dialog.warning(f"intents: {intents}")
        print(intents) 
        action = await self.ms_list[self.cur_moral_id].oai_interface.get_composition(intents, replic)
        emotion = await self.ms_list[self.cur_moral_id].oai_interface.get_composition(hlp.emotion_space, replic)

        if emotion[0] >= emotion[1]:
            emotion[1] = 0
        if emotion[1] >= emotion[0]:
            emotion[1] = 0
        print("happy, sad, surprise, disgust, angry, afraid")
        print(f"emotions: {emotion}")
        self.logger_dialog.warning(f"action: {action}")
        if action is None:
            return "Не удалось связаться с сервером"
        self.logger_dialog.warning(action)
        self.ms_list[self.cur_moral_id].update_vectors(np.array(action))

        appr_state = self.ms_list[self.cur_moral_id].get_appraisals_state()
        feel_state = self.ms_list[self.cur_moral_id].get_feelings_state()
        dist = self.ms_list[self.cur_moral_id].euc_dist(appr_state, feel_state)

        self.logger_dialog.warning(f'appr:{self.ms_list[self.cur_moral_id].get_appraisals()}')
        self.logger_dialog.warning(f'feel:{self.ms_list[self.cur_moral_id].get_feelings()}')
        self.logger_dialog.warning(f'appr_state:{self.ms_list[self.cur_moral_id].get_appraisals_state()}')
        self.logger_dialog.warning(f'feel_state:{self.ms_list[self.cur_moral_id].get_feelings_state()}')

        diff = appr_state-feel_state

        self.logger_dialog.warning(f'diff: {diff}')

        self.prev_moral_id = self.cur_moral_id


        if self.cur_moral_id <=2:
            condition = await self.ms_list[self.cur_moral_id].oai_interface.get_brain_status(self.messages, replic, self.cur_moral_id)

            self.logger_dialog.warning(f'cond: {condition}')

            if "да" in condition.lower():
                self.brain[self.cur_moral_id] = True
                self.cur_moral_id = min(self.cur_moral_id + 1, 3 )

        if dist < 0.25: #проверка на превосходство крит. точки
            self.schemes[self.cur_moral_id] = True #Для начала ставим статус текущей схемы в тру
            ##self.cur_moral_id = min(self.cur_moral_id + 1, 2 ) #переходим на след схему, 3 - это число сколько всего схем
        
        self.logger_dialog.warning(f'cur: {self.cur_moral_id}')
        self.logger_dialog.warning(f'prev: {self.prev_moral_id}')
            
        reply = await self.ms_list[self.cur_moral_id].oai_interface.get_replic(replic, self.messages, intents, diff, self.prev_moral_id, self.cur_moral_id) #генерируем овтет бота
        print(reply)
        if TTS == False:
            content = await self.ms_list[self.cur_moral_id].oai_interface.get_short(reply) # генерируем запись на доске
        
        print ("ттсчекпойнт")
        if TTS == True:
            print ("TTS стоит как тру")
            TTS_path = await self.ms_list[self.cur_moral_id].oai_interface.get_tts(model=self.model, voice=self.voice, input=reply) # генерируем голос если надо
            print(f"результат ттс:{TTS_path}")
            #TTS_path = self.generate_TTS(reply)
        
        if TTS == False:
            print(f"short content: {content}")
        self.messages.append({"role": "user", "content": replic}) #обновляем историю диалога
        self.messages.append({"role": "assistant", "content": reply}) #обновляем историю диалога       
        
        if TTS == True:
            return {
                "Reply": reply,
                #"Short": content,
                "TTS": TTS_path,
                #"Emotions": self.feelings_to_emotions()
                "Emotions": emotion
                } 
        else:
            return {
            "Reply": reply,
            "Short": content,
            "Emotions": emotion
            } 
