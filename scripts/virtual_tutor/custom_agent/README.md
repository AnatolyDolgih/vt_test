# Пример кастомного агента

Директория `custom_agent` демонстрирует, как собрать собственного бота поверх архитектуры Virtual Tutor и `new_ui`.
Пример показывает, как переиспользовать готовый `VirtualTutor`, добавить простое FastAPI-API и интегрироваться с new_ui через HTTP.

## Структура
- `agent.py` — обертка над `VirtualTutor` c готовым методом `respond`.
- `server.py` — минимальный FastAPI-сервер с роутом `/custom_agent/reply` для общения с агентом (подходит для new_ui или любого клиента).
- `README.md` — краткое описание и сценарии запуска.

## Настройка окружения
1. Перейдите в `scripts/virtual_tutor` и создайте виртуальное окружение:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Установите зависимости FastAPI, Uvicorn и aiohttp (для `VirtualTutor`):
   ```bash
   pip install fastapi uvicorn "pydantic<2.0" aiohttp
   ```
3. Скопируйте `config.yaml.example` в `config.yaml` и пропишите API-ключи, модели и адреса провайдеров для LLM/TTS/STT. Эти значения считываются `server.helper.load_config()` внутри `VirtualTutor`.

## Запуск агента
1. Запустите uvicorn из корня репозитория (важно указать полный путь к модулю, чтобы корректно подхватились импорты):
   ```bash
   uvicorn scripts.virtual_tutor.custom_agent.server:app --reload --host 0.0.0.0 --port 5051
   ```
2. Проверьте API с помощью curl:
   ```bash
   curl -X POST "http://localhost:5051/custom_agent/reply" \
        -H "Content-Type: application/json" \
        -d '{"text": "Помоги написать план эссе", "tts": false}'
   ```
   Ответ вернет текст агента, а при `"tts": true` дополнительно вернется путь к сгенерированному аудио (`TTS`).

## Интеграция с new_ui
- new_ui уже работает поверх FastAPI. Можно подключить кастомный агент как backend-обработчик: отправляйте пользовательские сообщения на `/custom_agent/reply` вместо `/chat/messages`.
- Для подключения WebSocket/статусов можно переиспользовать существующие эндпоинты из `src/unified_server.py` и просто заменить вызовы генерации текста на `CustomAgent.respond()`.

## Расширение
- Метод `CustomAgent.respond` возвращает и текст, и TTS по необходимости; сюда можно добавить логику выбора модели, метаданные сессии или интеграцию с собственной базой знаний.
- Если нужен другой стартовый промпт или набор голосов, измените параметры `CustomAgent` в `server.py`.
