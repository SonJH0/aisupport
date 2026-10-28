from pathlib import Path
from typing import Literal
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from ai.agent import respond
from ai.vision import analyze_image

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
app = FastAPI(title="AI 취업 비서")
app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")

class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=10000)

class Request(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    image: str | None = Field(default=None, max_length=6000000)
    history: list[Message] = Field(default_factory=list, max_length=10)

@app.get("/")
def index():
    return FileResponse(ROOT / "frontend" / "index.html")

@app.post("/api/chat")
def chat(req: Request):
    try:
        history = [item.model_dump() for item in req.history]
        if req.image:
            return analyze_image(req.message, req.image, history=history)
        return respond(req.message, history=history)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(502, "AI 서비스에 연결하지 못했습니다. API 키와 모델 설정을 확인해 주세요.") from e
