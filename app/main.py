import asyncio
import json
import os
from pathlib import Path
from typing import Literal
from urllib import error, request as urllib_request

from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.rag_query import answer as rag_answer
from app.rag_query import rag_is_configured

app = FastAPI(title="MD-Hackathon Dashboard")

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# ---------------------------------------------------------------------------
# Dummy data
# ---------------------------------------------------------------------------
DUMMY_DATA = {
    "title": "MD-Hackathon Dashboard",
    "llm_configured": False,
    "stats": [
        {"label": "Total Projects", "value": 42, "icon": "📁"},
        {"label": "Active Users", "value": 128, "icon": "👥"},
        {"label": "Tasks Completed", "value": 317, "icon": "✅"},
        {"label": "Uptime", "value": "99.9 %", "icon": "⚡"},
    ],
    "recent_activity": [
        {"user": "Alice", "action": "Submitted proposal", "time": "2 min ago"},
        {"user": "Bob", "action": "Updated dataset", "time": "15 min ago"},
        {"user": "Carol", "action": "Opened issue #84", "time": "1 hr ago"},
        {"user": "Dave", "action": "Merged pull request", "time": "3 hr ago"},
        {"user": "Eve", "action": "Deployed to staging", "time": "5 hr ago"},
    ],
    "projects": [
        {"name": "Alpha", "status": "Active", "progress": 75},
        {"name": "Beta", "status": "Active", "progress": 50},
        {"name": "Gamma", "status": "Paused", "progress": 30},
        {"name": "Delta", "status": "Completed", "progress": 100},
    ],
}


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    mode: Literal["chat", "rag"] = "chat"


class ChatResponse(BaseModel):
    response: str


def llm_is_configured() -> bool:
    return bool(os.getenv("SERVER_URL") and os.getenv("SERVER_TOKEN"))


def post_llm_chat(messages: list[dict[str, str]]) -> dict:
    server_url = os.getenv("SERVER_URL")
    server_token = os.getenv("SERVER_TOKEN")

    if not server_url or not server_token:
        raise HTTPException(
            status_code=503,
            detail="LLM backend is not configured. Set SERVER_URL and SERVER_TOKEN.",
        )

    endpoint = f"{server_url.rstrip('/')}/api/llm/chat"
    payload = json.dumps({"messages": messages}).encode("utf-8")
    req = urllib_request.Request(
        endpoint,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {server_token}",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(
            status_code=exc.code,
            detail=f"LLM backend request failed: {detail}",
        ) from exc
    except error.URLError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM backend is unreachable: {exc.reason}",
        ) from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail="LLM backend returned invalid JSON.",
        ) from exc

    if "response" not in parsed or not isinstance(parsed["response"], str):
        raise HTTPException(
            status_code=502,
            detail="LLM backend returned an unexpected response format.",
        )

    return parsed


def post_rag_chat(messages: list[dict[str, str]]) -> str:
    user_prompt = next(
        (message["content"] for message in reversed(messages) if message["role"] == "user"),
        None,
    )
    if not user_prompt:
        raise HTTPException(status_code=400, detail="No user message provided.")

    try:
        return rag_answer(user_prompt, history=messages)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"RAG backend request failed: {exc}",
        ) from exc


@app.get("/")
async def dashboard(request: Request):
    context = {
        **DUMMY_DATA,
        "llm_configured": llm_is_configured(),
        "rag_configured": rag_is_configured(),
    }
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=context,
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    # Keep the context short to match the platform's limited token window.
    messages = [message.model_dump() for message in payload.messages[-8:]]
    if payload.mode == "rag":
        response = await asyncio.to_thread(post_rag_chat, messages)
        return ChatResponse(response=response)

    response = await asyncio.to_thread(post_llm_chat, messages)
    return ChatResponse(response=response["response"])
