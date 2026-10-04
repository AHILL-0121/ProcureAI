import asyncio
import json

import httpx
import pytest

from app.agents.vision_ocr import VisionOCRAgent
from app.config import settings


@pytest.fixture(autouse=True)
def groq_settings(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(settings, "groq_model", "text-model")
    monkeypatch.setattr(settings, "groq_vision_model", "vision-model")
    yield
    VisionOCRAgent.last_check = None
    VisionOCRAgent._health_cache = None


def agent(handler) -> VisionOCRAgent:
    return VisionOCRAgent(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def reply(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def test_both_models_answer_correctly():
    def handler(request: httpx.Request):
        body = json.loads(request.content)
        if body["model"] == "text-model":
            assert body["response_format"] == {"type": "json_object"}
            return reply('{"total": 42}')
        assert body["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")
        return reply("4719")

    r = asyncio.run(agent(handler).startup_check())
    assert r["text"]["ok"] and not r["text"]["warning"] and r["text"]["detail"] == "JSON mode OK"
    assert r["vision"]["ok"] and not r["vision"]["warning"]


def test_unknown_vision_model_fails_and_marks_vision_unavailable():
    def handler(request: httpx.Request):
        if json.loads(request.content)["model"] == "text-model":
            return reply('{"total": 42}')
        return httpx.Response(404, json={"error": {"message": "The model `vision-model` does not exist",
                                                   "code": "model_not_found"}})

    r = asyncio.run(agent(handler).startup_check())
    assert r["text"]["ok"]
    assert not r["vision"]["ok"] and "HTTP 404" in r["vision"]["detail"] and "does not exist" in r["vision"]["detail"]


def test_wrong_answers_are_warnings_not_failures():
    def handler(request: httpx.Request):
        if json.loads(request.content)["model"] == "text-model":
            return reply('{"total": 41}')
        return reply("I can't see any image")

    r = asyncio.run(agent(handler).startup_check())
    assert r["text"]["ok"] and r["text"]["warning"]
    assert r["vision"]["ok"] and r["vision"]["warning"] and "misread" in r["vision"]["detail"]


def test_missing_key_and_disabled_vision(monkeypatch):
    # conftest pretends Groq is configured; use the real rule here
    monkeypatch.setattr(VisionOCRAgent, "configured", property(lambda self: bool(settings.groq_api_key)))
    monkeypatch.setattr(settings, "groq_api_key", "")
    r = asyncio.run(VisionOCRAgent().startup_check())
    assert not r["text"]["ok"] and "not set" in r["text"]["detail"] and r["vision"] is None

    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(settings, "groq_vision_model", "")
    r = asyncio.run(agent(lambda req: reply('{"total": 42}')).startup_check())
    assert r["text"]["ok"] and r["vision"] is None
