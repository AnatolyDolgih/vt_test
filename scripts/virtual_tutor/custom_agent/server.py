from __future__ import annotations

from aiohttp import ClientSession
from fastapi import FastAPI
from pydantic import BaseModel

from .agent import CustomAgent

app = FastAPI(title="Custom Virtual Tutor")


class Message(BaseModel):
    text: str
    tts: bool = False


@app.on_event("startup")
async def startup() -> None:
    session = ClientSession()
    app.state.session = session
    app.state.agent = CustomAgent(session=session)


@app.on_event("shutdown")
async def shutdown() -> None:
    session: ClientSession = app.state.session
    await session.close()


@app.post("/custom_agent/reply")
async def reply(message: Message):
    agent: CustomAgent = app.state.agent
    return await agent.respond(message.text, tts=message.tts)
