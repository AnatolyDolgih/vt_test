from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

from aiohttp import ClientSession

# Добавляем путь к исходникам Virtual Tutor, чтобы переиспользовать готовые классы
SRC_ROOT = Path(__file__).resolve().parent.parent / "src"
sys.path.append(str(SRC_ROOT))

from server.virtual_tutor import VirtualTutor  # type: ignore  # pylint: disable=import-error


class CustomAgent:
    """Обертка над VirtualTutor с простым методом для получения ответа."""

    def __init__(self, *, session: ClientSession, model: str = "tts-1", voice: str = "nova") -> None:
        self.session = session
        self._agent = VirtualTutor(
            m_id="custom-agent",
            start_msg="Привет! Я кастомный ассистент и помогу написать эссе.",
            session=self.session,
            model=model,
            voice=voice,
        )

    async def respond(self, message: str, *, tts: bool = False) -> Dict[str, Any]:
        """Вернуть текст агента и, опционально, TTS."""

        reply = await self._agent.generate_answer(message, TTS=tts)
        response: Dict[str, Any] = {"text": reply}

        if tts:
            response.update(await self._agent.generate_TTS(reply))

        return response
