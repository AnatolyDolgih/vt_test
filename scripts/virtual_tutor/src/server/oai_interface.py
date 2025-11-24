import re
import os
import json
import aiohttp
import asyncio
from dotenv import load_dotenv
from typing import List, Dict, Optional
import uuid
from . import helper as hlp

load_dotenv()
# Настройки берём из config.yaml через helper.load_config() в __init__

class Interface:
    def __init__(self, session: Optional[aiohttp.ClientSession]):
        cfg = hlp.load_config()
        llm = (cfg or {}).get('llm', {})
        provider = llm.get('provider', 'openai_proxy')
        # Ключ: приоритет — llm.api_key -> env[llm.api_key_env] -> PROXY_TOKEN -> OPENAI_API_KEY
        api_key = llm.get('api_key') or (os.getenv(llm.get('api_key_env','')) if llm.get('api_key_env') else None)
        api_tts = llm.get('api_tts') or (os.getenv(llm.get('api_tts_env','')) if llm.get('api_tts_env') else "https://www.bicaai2023.org/openai_tts_generate/v1/chat/completions")

        api_key = api_key or os.getenv('PROXY_TOKEN') or os.getenv('OPENAI_API_KEY')
        bearer_token = os.getenv('PROXY_TOKEN') or None
        self.header_tts = {'Authorization': f'Bearer {bearer_token}'}
        if not api_key:
            raise ValueError('Не найден API-ключ. Укажите llm.api_key или llm.api_key_env в config.yaml, либо задайте переменную окружения.')

        # База URL: приоритет — llm.api_base -> дефолт по провайдеру -> PROXY_OPENAI_URL (для openai_proxy) -> дефолт OpenAI
        provider_defaults = {
            'openai': 'https://api.openai.com/v1',
            'openai_proxy': os.getenv('PROXY_OPENAI_URL'),
            'deepseek': 'https://api.deepseek.com/v1',
            'qwen': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        }
        api_base = llm.get('api_base')
        if not api_base:
            api_base = provider_defaults.get(provider)
        if not api_base:
            api_base = 'https://api.openai.com/v1'

        self.api_base = str(api_base).rstrip('/')
        self.api_tts = str(api_tts).rstrip('/')
        self.provider = provider
        self.header = {'Authorization': f'Bearer {api_key}'}
        self.client_session = session

        # Модели из конфига (с дефолтами)
        self.model_chat = llm.get('model_chat', 'gpt-4o-mini')
        self.model_tts  = llm.get('model_tts',  'tts-1')
        self.tts_voice  = llm.get('tts_voice',  'nova')
        self.model_stt  = llm.get('model_stt',  'whisper-1')
        
    def clear_intentions(self, reply: str) -> List[float]:
        print(reply)
        """
        Обработка полученных интенций из текста в список чисел.

        Аргументы:
            reply (str): Текст ответа от chatGPT для извлечения интенций.

        Возвращает:
            List[float]: Список числовых значений интенций.
        """
        if not isinstance(reply, str):
            raise ValueError("reply не строка")
        numbers = re.findall(r"[-+]?\d*\.\d+|\d+", reply)
        numbers = [float(num) if '.' in num else int(num) for num in numbers]
        
        # TODO: костыль, надо будет аккуратно убрать!
        if len(numbers) <= 0:
            numbers = [0, 0, 0, 0, 0, 0, 0, 0]
        
        return numbers 

    async def get_short(self, reply: str):
        string = f'''
            Представь, что ты преподаватель. Тебе нужно на доске записать кратко данную реплику: {reply}. 
            в виде буллетов. В качестве символа буллета используй звездочку. В каждом буллете не более 3 слов. 
            Выдай фразу на английском языке. 
        '''
        body = {
            'model': self.model_chat,
            'messages': [{'role': 'assistant', 'content': string }]
        }
        for attempt in range(5):
            try:
                async with self.client_session.post(url=self.api_base, headers=self.header,json=body) as response:
                    response.raise_for_status()
                    reply = await response.json()
                    return reply["choices"][0]["message"]["content"]
            except (aiohttp.ClientError, KeyError, json.JSONDecodeError) as e:
                if attempt == 4:
                    print(f"Ошибка при запросе к серверу: {e}")
                    return None
                await asyncio.sleep(2)


    async def get_composition(self, intents_dict: Dict[int, str], fraze: str) -> Optional[List[float]]:
        """
        Получение композиции интенций на основе фразы.

        Аргументы:
            intents_dict (Dict[int, str]): Словарь интенций.
            fraze (str): Фраза для анализа.

        Возвращает:
            Optional[List[float]]: Список интенций с их вероятностями, либо None в случае ошибки.
        """
        
        cat_str = ', '.join(intents_dict.values())
        num = len(intents_dict.values())
        
        string = f'''
                You are a mechanism for determining intentions in human speech related to his behavior
                in various social situations.
                Your main task is to determine the probability of containing each intention
                from the spoken sentence from 0 to 1. You have only {num}
                intensions to guess (they are listed separated by commas):
                {cat_str} Probability is a number from 0 to 1, where 0 - the intention is not contained at all,
                and 1 - it is contained exactly. Use intentions only from the specified list!
                Output {num} probability values ​​of each intentionality in the phrase:
                "{fraze}"
                Output only the values ​​separated by commas'''
        ####################################################
        # string = f'''
        #         Ты механизм по определению интенций в речи человека, связанных с его поведением 
        #         в различных социальных ситуациях.
        #         Твоей основной задачей является определить вероятность содержания каждой интенции 
        #         из сказанного предложения от 0 до 1. В твоем распоряжении только {num} 
        #         интенсиональностей для угадывания (они перечислены через запятую):
        #         {cat_str} Вероятность - число от 0 до 1, где 0 - интенция не содержится совсем, 
        #         а 1 - содержится точно. Используй интенции только из указанного списка! 
        #         Выведи {num} значений вероятности каждой интенциональности в фразе:  
        #         "{fraze}"
        #         Выведи только значения через запятую
        # '''
        body = {
            'model': self.model_chat,
            'messages': [{'role': 'assistant', 'content': string }]
        }
        for attempt in range(5):
            try:
                async with self.client_session.post(url=self.api_base, headers=self.header,json=body) as response:
                    response.raise_for_status()
                    reply = await response.json()
                    
                    print(f'''Reply1: {reply["choices"][0]["message"]["content"]}''')
                    return self.clear_intentions(reply["choices"][0]["message"]["content"])
            except (aiohttp.ClientError, KeyError, json.JSONDecodeError) as e:
                if attempt == 4:
                    print(f"Ошибка при запросе к серверу: {e}")
                    return None
                await asyncio.sleep(2)

    async def get_tts(self, voice: str, input: str, model: str):
        # if self.provider not in ('openai', 'openai_proxy'):
        #     raise NotImplementedError('TTS доступен только для openai/openai_proxy в текущей реализации.')
        # if self.provider not in ('openai', 'openai_proxy'):
        #     raise NotImplementedError('TTS доступен только для openai/openai_proxy в текущей реализации.')
        voice = voice or self.tts_voice
        model = model or self.model_tts
        body = {
            'model': model, #tts-1
            'voice': voice, #nova
            'input': input
        }
        for attempt in range(5):
            try:
                print(f"ШЛЁМ ЗАПРОС НА {self.api_tts}")
                async with self.client_session.post(url=self.api_tts, headers=self.header_tts, json=body) as response:
                    #if response.status_code == 200:
                        # Get the suggested filename from the Content-Disposition header, if available
                        print(response)
                        file_id = str(uuid.uuid4()) # генерация уникального айди файла, в который будут записываться все результаты STT
                        file_path = f"output_{file_id}.wav"
                        filename = file_path

                        # Save the content to a local file
                        with open(filename, "wb") as f:
                            data_in_bytes = await response.content.read()
                            f.write(data_in_bytes)
                        print(f"File '{filename}' downloaded successfully.")
                        return (filename)
                    #else:
                    #    return "Не удалось связаться с сервером 12121323123"
            except (aiohttp.ClientError, aiohttp.ClientResponseError, json.JSONDecodeError, KeyError, asyncio.TimeoutError) as e:
                if attempt == 4:
                    print(f"Ошибка связи с сервером: {e}")
                    reply = str(e)
                    return reply
                await asyncio.sleep(2)
            except Exception as e:
                if attempt == 2:
                    print(f"Непредвиденная ошибка: {e}")
                    return f"Непредвиденная ошибка: {e}"
                await asyncio.sleep(2)

    async def get_replic(self, last_message: str, messages: List[Dict[str, str]], 
                         intens_dict: Dict[int, str], feelings: List[float],
                         prev_scheme: int, current_scheme: int) -> str:
        """
        Генерация новой реплики на основе предыдущих сообщений и схемы.

        Аргументы:
            last_message (str): Последнее сообщение.
            messages (List[Dict[str, str]]): Список сообщений.
            intens_dict (Dict[int, str]): Словарь интенций.
            feelings (List[float]): Список значений чувств.
            prev_scheme (int): Предыдущая схема.
            current_scheme (int): Текущая схема.

        Возвращает:
            str: Ответ на последнюю реплику.
        """
        rlt = [(intens_dict[i if val > -0.05 else -i], val) for i, val in enumerate(feelings, start=1)]
        student_profile = '''Характеристика студента: \n'''

        # Перечисляем элементы
        for idx, (dict_value, list_value) in enumerate(rlt, start=1):
            fnt = f"Студент {dict_value}\n"
            student_profile += fnt
    
        for idx, (dict_value, list_value) in enumerate(rlt, start=1):
            if list_value < -0.05:
                mov = f"Студент оказался {dict_value}. \
                    Необходимо окрасить свой ответ так, чтобы это поспособствовало \
                    положительной смене этой характеристики"   
                student_profile += mov

        changed_message = f'''
                        The person's last remark: {last_message}.
                        Generate a phrase - a response to the person's last remark
                        The phrase must be an adequate and logical response to the person's last remark.
                        The phrase must be appropriate in the context of the entire dialogue history.
                        The phrase must be no longer than 50 words.
                        The phrase must not contain any information about the dialogue stages
                        Output only the new remark.
                        You must change your answer taking into account the student's characteristics: {student_profile}
                        Parameters for transitions between stages:
                        '''
        ##################################################################
        # changed_message = f'''Последняя реплика человека:{last_message}.
        #     Сгенерируй фразу - ответ на последнюю реплику человека
        #     Фраза должна быть адекватным и логичным ответом к последней реплике человека.
        #     Фраза должна быть уместной в контексте всей истории диалога.
        #     Фраза должна быть не длинне 50 слов.
        #     Фраза не должна содержать никакой информации об этапах диалога
        #     Выведи только новую реплику.
        #     Ты должен поменять свой ответ с учетом характеристики студента: {student_profile}
        #     Параметры по переходам между этапами:
        #     '''

        if current_scheme-prev_scheme == 1 and current_scheme == 2:
            changed_message =  changed_message + hlp.from1to2 
        elif current_scheme-prev_scheme == 2 and current_scheme == 3:
            changed_message =  changed_message + hlp.from2to3
        elif current_scheme-prev_scheme == 3 and current_scheme == 4:
            changed_message =  changed_message + hlp.from3to4
        elif current_scheme == prev_scheme:
            changed_message =  changed_message + \
                f"Вы находитесь на {current_scheme+1} этапе. Переходить пока не нужно" 

        messages_opt = list(messages)
        messages_opt.append({"role": "user", "content": changed_message})
        
        body = {
            'model': self.model_chat,
            'messages': messages_opt,
        }
        
        for attempt in range(5):
            try:
                async with self.client_session.post(url=self.api_base, headers=self.header, json=body) as response:
                    response.raise_for_status()
                    reply = await response.json()
                    #reply = json.loads(json.dumps(reply))
                    print(f'''reply2: {reply["choices"][0]["message"]["content"]}''')
                    return reply["choices"][0]["message"]["content"]
            except (aiohttp.ClientError, KeyError, json.JSONDecodeError) as e:
                if attempt == 4:
                    print(f"Ошибка при запросе к серверу: {e}")
                    return "Не удалось связаться с сервером"
                await asyncio.sleep(2)


    async def get_dummy_replic(self, messages):
        body = {
            'model': self.model_chat,
            'messages': messages,
        }
        for attempt in range(5):
            try:
                async with self.client_session.post(url=self.api_base, headers=self.header, json=body) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        return "Не удалось связаться с сервером"
            except (aiohttp.ClientError, aiohttp.ClientResponseError, json.JSONDecodeError, KeyError, asyncio.TimeoutError) as e:
                if attempt == 4:
                    print(f"Ошибка связи с сервером: {e}")
                    reply = "Не удалось связаться с сервером"
                    return reply
                await asyncio.sleep(2)
            except Exception as e:
                if attempt == 4:
                    print("Непредвиденная ошибка")
                    return f"Непредвиденная ошибка"
                await asyncio.sleep(2)
        

    async def get_brain_status(self, messages, last_message,  current_scheme):
        changed_message =""
        if current_scheme == 0:
          changed_message = f'''Последняя реплика человека:{last_message}.
            Сейчас ты находишься на первом этапе диалога. Вы общаетесь со студентом и 
            условие перехода на следующий этап - получено формальное согласие студента начать 
            занятие.
            Оцени по последнему сообщению было ли получено это  согласие. В ответе выведи только 
            "да" или "нет" в зависимости от выполнения условия
            '''

        elif current_scheme == 1:
          changed_message = f'''Последняя реплика человека:{last_message}.
            Сейчас ты находишься на втором этапе. Сейчас вы работаете на написанием outline. 
            Проверь по последнему сообщению - является ли оно написанным студентом outline.
            Исключение: если последнее сообщение все-таки является написанным outline, но 
            сильно не соответствует каким-то критериям , то ответ должен быть "нет"
           В ответе выведи только "да" или "нет" в зависимости от выполнения условия
            '''

        elif current_scheme == 2:
          changed_message = f'''Последняя реплика человека:{last_message}.
            Сейчас ты находишься на третьем этапе. Сейчас вы работаете над написанием самого эссе. 
            Проверь по последнему сообщению и истории- написал ли студент эссе полностью, включая заключение?
            Исключение: если последнее сообщение все-таки является полностью написанным эссе, но сильно не 
            соответствует каким-то критериям , то ответ должен быть "нет"
            В ответе выведи только "да" или "нет" в зависимости от выполнения условия
            '''
        else:
           return
        messages_opt = list(messages)
        messages_opt.append({"role": "user", "content": changed_message})
        
        
        body = {
            'model': self.model_chat,
            'messages': messages_opt,
        }
        
        for attempt in range(5):
            try:
                async with self.client_session.post(url=self.api_base, headers=self.header, json=body) as response:
                    response.raise_for_status()
                    reply = await response.json()
                    #reply = json.loads(json.dumps(reply))
                    print(f'''reply2: {reply["choices"][0]["message"]["content"]}''')
                    return reply["choices"][0]["message"]["content"]
            except (aiohttp.ClientError, aiohttp.ClientResponseError, KeyError, json.JSONDecodeError) as e:
                if attempt == 4:
                    print(f"Ошибка при запросе к серверу {e}")
                    return "Не удалось связаться с сервером"
                await asyncio.sleep(2)
                
    async def test_model(self, reply: str):
        string = f'''
            Развернуто ответь на реплику {reply}, но твой ответ не должен быть длинее, чем 5 предложений. 
        '''
        body = {
            'model': self.model_chat,
            'messages': [{'role': 'assistant', 'content': string }]
        }
        for attempt in range(5):
            try:
                async with self.client_session.post(url=self.api_base, headers=self.header,json=body) as response:
                    response.raise_for_status()
                    reply = await response.json()
                    return reply["choices"][0]["message"]["content"]
            except (aiohttp.ClientError, KeyError, json.JSONDecodeError) as e:
                if attempt == 4:
                    print(f"Ошибка при запросе к серверу: {e}")
                    return None
                await asyncio.sleep(2)  