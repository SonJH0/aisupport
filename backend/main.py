from pathlib import Path
from typing import Literal
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
import logging
import os
import time
import uuid
import traceback
from contextvars import ContextVar
import httpx
from ai.errors import ServiceError
from ai.agent import respond
from ai.vision import analyze_image

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
app = FastAPI(title="AI 취업 비서", version="0.3.1")
logger = logging.getLogger(__name__)
request_context = ContextVar("request_id", default="unknown")
app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")

class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=10000)

class Request(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    image: str | None = Field(default=None, max_length=6000000)
    history: list[Message] = Field(default_factory=list, max_length=10)
    consent: bool = False

    @field_validator("message")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("질문이나 경험을 입력해 주세요.")
        return value.strip()

@app.middleware("http")
async def request_diagnostics(request, call_next):
    request_id = uuid.uuid4().hex
    request_context.set(request_id)
    started = time.monotonic()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    if request.url.path == "/api/chat":
        logger.warning("chat_request request_id=%s status=%s duration_ms=%s revision=%s",
                       request_id, response.status_code,
                       round((time.monotonic() - started) * 1000),
                       os.getenv("RENDER_GIT_COMMIT", "unknown")[:40])
    return response


@app.get("/")
def index():
    return FileResponse(ROOT / "frontend" / "index.html")

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.3.1",
            "revision": os.getenv("RENDER_GIT_COMMIT", "unknown")[:40]}

@app.post("/api/chat")
def chat(req: Request):
    if not req.consent:
        raise HTTPException(403, "AI 처리를 위한 외부 전송 동의가 필요합니다.")
    try:
        history = [item.model_dump() for item in req.history]
        if req.image:
            return analyze_image(req.message, req.image, history=history)
        return respond(req.message, history=history)
    except ServiceError as error:
        logger.warning("chat_service_error request_id=%s status=%s category=%s", request_context.get(), error.status_code, error.code)
        raise HTTPException(error.status_code, str(error)) from None
    except ValueError:
        raise HTTPException(400, "입력 내용과 이미지 형식, 서버의 키 설정을 확인해 주세요.") from None
    except httpx.TimeoutException:
        raise HTTPException(504, "이미지 분석 응답 시간이 초과되었습니다.") from None
    except httpx.HTTPError:
        raise HTTPException(502, "이미지 분석 서비스 연결 또는 인증에 실패했습니다.") from None
    except Exception as error:
        # 예외 본문·지역 변수·사용자 입력·인증 값은 기록하지 않는다.
        frames = ";".join(f"{Path(frame.filename).name}:{frame.lineno}:{frame.name}"
                          for frame in traceback.extract_tb(error.__traceback__)[-6:])
        logger.error("chat_unexpected_error request_id=%s category=%s frames=%s", request_context.get(), type(error).__name__, frames)
        raise HTTPException(500, "요청 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.") from None
