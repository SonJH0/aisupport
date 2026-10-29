import json
import pytest
from ai import agent
from ai.errors import ServiceError
from test_agent_api import FakeClient,completion

@pytest.mark.parametrize('raw',['먼저 자료를 확인하겠습니다.','{}','[]','{"calls":[]}'])
def test_learning_plan_failure_executes_local_retrieval(monkeypatch,raw):
    monkeypatch.setenv('AGENT_TOOL_MODE','json')
    monkeypatch.setattr(agent,'search_live_jobs',lambda *a,**kw:pytest.fail('외부 공고 검색 금지'))
    client=FakeClient([completion(raw),completion('MDN 폼 학습 자료 [frontend-1]')])
    result=agent.respond('HTML 폼과 접근성을 배우려면 어떤 자료를 참고하나요?',client=client)
    assert result['tools']==['search_documents']
    payload=json.loads(client.requests[-1]['messages'][-1]['content'])
    assert payload['tool_results'][0]['result']['documents']
    assert any(t['status'].endswith('document_fallback') for t in result['trace'])

@pytest.mark.parametrize('message',['Python 신입 공고 자료를 검색해 주세요.','[지원자의 경험]\nPython\n[채용공고]\nPython 개발 경험'])
def test_required_search_and_comparison_do_not_fall_back_to_learning(monkeypatch,message):
    monkeypatch.setenv('AGENT_TOOL_MODE','json')
    with pytest.raises(ServiceError):agent.respond(message,client=FakeClient([completion('{}')]))

def test_unknown_tool_is_still_rejected_for_learning(monkeypatch):
    monkeypatch.setenv('AGENT_TOOL_MODE','json')
    with pytest.raises(ServiceError):agent.respond('HTML 학습 자료를 알려주세요.',client=FakeClient([completion('{"calls":[{"name":"run_shell","arguments":{}}]}')]))
