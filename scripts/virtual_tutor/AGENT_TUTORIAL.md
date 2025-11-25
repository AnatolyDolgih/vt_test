# Туториал по созданию агентов на основе Virtual Tutor

Ниже описаны шаги, которые помогут быстро запустить new_ui, подключить сервер Virtual Tutor и собрать собственного агента поверх существующих компонентов репозитория.

## 1. Архитектура
- Единый FastAPI‑сервер (`src/unified_server.py`) обслуживает оба интерфейса: новый UI доступен по путям `/new` и `/static`, а старый — по `/legacy` и использует те же HTTP/WebSocket‑эндпоинты для тем, эссе и чата.
- При запуске из `src/new_ui/server.py` поднимается тот же экземпляр приложения `app`, поэтому UI и API всегда синхронизированы.
- Главная страница (`/`) отдает `select_theme.html`, позволяя выбрать тему до старта сессии, а `/essay_editor` загружает основной экран new_ui.

## 2. Подготовка окружения
1. Используйте Python 3.11.
2. Создайте виртуальное окружение и установите зависимости сервера и тестов:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install fastapi uvicorn "pydantic<2.0" websockets pytest
   ```

## 3. Запуск unified-сервера
Из директории `scripts/virtual_tutor/src` выполните:
```bash
uvicorn unified_server:app --reload --host 0.0.0.0 --port 5050
```
После запуска:
- new_ui доступен по `http://localhost:5050/new` (или `/static`).
- legacy UI — по `http://localhost:5050/legacy`.

## 4. Работа с new_ui
- Начните с `http://localhost:5050/` — загрузится выбор темы из `select_theme.html`.
- Для передачи темы UI вызывает `POST /set_theme` и считывает ее через `GET /get_theme` или `/get_theme_to_bica`.
- Вкладка эссе отправляет текст через `POST /essay_data/`, а бэкенд выдает следующие элементы очереди на `GET /get_data/`.
- История чата хранится в памяти: `POST /chat/messages` добавляет сообщение, `GET /chat/messages` возвращает массив.
- WebSocket `/wss/{client_type}` передает сигналы старта/остановки записи речи и обновляет флаг `/is_processing_done`.

## 5. Подключение виртуального тьютора
- Базовый тьютор описан в `src/server/virtual_tutor.py`. Он использует список моральных схем (`BaseMoralScheme`) и LLM‑интерфейс `Interface` для генерации ответов и TTS.
- Класс `VirtualAgentPrototype` можно применять как облегченную заготовку: ему достаточно стартового сообщения, модели и голоса.
- Полнофункциональный `VirtualTutor` ведет логи диалога/эссе, отслеживает текущую моральную схему (`self.cur_moral_id`) и может запрашивать TTS через `generate_TTS` или `generate_answer(..., TTS=True)`.

### Настройка LLM
- Пример `config.yaml.example` показывает, как описать провайдера, базовые URL и модели для чата, TTS и STT. Переменные окружения (`api_key_env`) позволяют скрыть ключи доступа.
- Создайте `config.yaml` рядом с примером и пропишите собственные ключи/модели. Функция `server.helper.load_config()` читает этот файл при инициализации интерфейсов.

### Минимальный код агента
```python
from server.virtual_tutor import VirtualTutor
from aiohttp import ClientSession

async def build_agent():
    session = ClientSession()
    tutor = VirtualTutor(
        m_id="demo",
        start_msg="Привет! Давай напишем эссе о машинном обучении.",
        session=session,
        model="tts-1",
        voice="nova",
    )
    reply = await tutor.generate_answer("Как лучше строить план?", TTS=False)
    await session.close()
    return reply
```
- Вызовите `generate_answer` из своего обработчика WebSocket или HTTP‑роута, чтобы встроить агента в текущие эндпоинты.

## 6. Готовый пример кастомного агента
В папке `custom_agent` находится минимальный сервер и обертка над `VirtualTutor`, чтобы можно было быстро собрать собственного бота:
- `custom_agent/agent.py` — класс `CustomAgent` с методом `respond`, который возвращает текст и, при необходимости, TTS.
- `custom_agent/server.py` — FastAPI‑сервер с роутом `/custom_agent/reply` (совместим с new_ui и любым клиентом).
Запуск:
```bash
cd scripts/virtual_tutor/custom_agent
uvicorn server:app --reload --host 0.0.0.0 --port 5051
curl -X POST "http://localhost:5051/custom_agent/reply" \
     -H "Content-Type: application/json" \
     -d '{"text":"Помоги придумать план эссе", "tts": false}'
```
В ответе вернется текст агента, а если передать `"tts": true`, дополнительно вернется путь к аудиофайлу.

## 7. Тестовые примеры и проверки
- Автотесты `tests/test_unified_server.py` покрывают статическую раздачу UI, установку темы, очередь эссе, хранение чата, флаг записи и echo‑канал legacy UI.
- Запустите их из корня репозитория:
  ```bash
  pytest scripts/virtual_tutor/tests/test_unified_server.py
  ```
- Для быстрой ручной проверки можно отправить запросы:
  ```bash
  curl -X POST http://localhost:5050/set_theme -H 'Content-Type: application/json' -d '{"topic":"AI"}'
  curl http://localhost:5050/get_theme
  curl -X POST http://localhost:5050/essay_data/ -H 'Content-Type: application/json' -d '{"text":"Essay text","language":"en"}'
  ```
Эти команды должны вернуть актуальную тему и статусы `success`, а `GET /get_data/` выдаст последнее эссе из очереди.
