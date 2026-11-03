import pytest
from fastapi.testclient import TestClient
import ai.agent as agent
import backend.main as api
from test_agent_api import FakeClient, completion, call

MESSAGE = "[지원자의 경험]\nPython으로 REST API를 개발한 경험이 있습니다. Java는 사용할 줄 모릅니다.\n[채용공고]\nPython 개발 경험\nJava 개발 경험\nKotlin 개발 경험"

@pytest.mark.parametrize("mode", ["native", "json"])
def test_advice_does_not_invent_unmentioned_experience(monkeypatch, mode):
    monkeypatch.setenv("AGENT_TOOL_MODE", mode)
    plan = completion(calls=[call("compare_requirements")]) if mode == "native" else completion('{"calls":[{"name":"compare_requirements","arguments":{}}]}')
    result = agent.respond(MESSAGE, client=FakeClient([plan, completion("Java·Kotlin 미보유를 표시하세요.")]))
    text = result["answer"]
    assert "Java·Kotlin 미보유" not in text
    kotlin = text.split("요건: Kotlin")[1]
    assert "판정: 정보 부족" in kotlin
    assert "경험 유무를 먼저 확인" in kotlin
    assert "요건: Python 개발 경험\n판정: 일치" in text
    assert "요건: Java 개발 경험\n판정: 차이" in text


def test_error_diagnostics_do_not_log_input_or_exception_secret(monkeypatch, caplog):
    def broken(*args, **kwargs):
        raise RuntimeError("SECRET_TEST_VALUE")
    monkeypatch.setattr(api, "respond", broken)
    with TestClient(api.app) as client:
        result = client.post("/api/chat", json={"message":"PRIVATE_INPUT", "consent":True})
    assert result.status_code == 500
    assert result.headers["X-Request-ID"] in caplog.text
    assert "RuntimeError" in caplog.text
    assert "SECRET_TEST_VALUE" not in caplog.text
    assert "PRIVATE_INPUT" not in caplog.text


def test_revision_and_visible_notice(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "a"*40)
    with TestClient(api.app) as client:
        assert client.get("/health").json()["revision"] == "a"*40
        html = client.get("/").text
        assert html.index("AI가 생성한 참고 정보") < html.index('id="messages"')
