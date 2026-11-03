import json
import pytest
from ai import agent
from ai.comparison import compare_requirements
from test_agent_api import FakeClient, completion, call

@pytest.mark.parametrize('message', [
 'Python으로 REST API 프로젝트를 만들었습니다. 제 스펙의 강점을 분석해 주세요. 공고 검색은 하지 마세요.',
 'Python REST API와 SQL 경험이 있습니다. 개발 직무 후보 2개와 이유를 제안해 주세요. 채용공고 검색은 하지 마세요.',
 'HTML 프로젝트와 pandas 경험의 강점을 분석해 주세요.',
])
@pytest.mark.parametrize('mode', ['auto', 'json'])
def test_skill_names_do_not_force_tool_plan(monkeypatch, message, mode):
    monkeypatch.setenv('AGENT_TOOL_MODE', mode)
    assert not agent._requires_tool(message)
    responses = [completion('입력 경험에 근거한 조언입니다.')]
    if mode == 'json':
        responses = [completion('{"calls":[]}'), *responses]
    client = FakeClient(responses)
    assert agent.respond(message, client=client)['answer'].startswith('입력 경험')


def test_repeated_search_finishes_with_actual_results(monkeypatch):
    monkeypatch.setenv('AGENT_TOOL_MODE', 'auto')
    responses = [completion(calls=[call('search_documents', '{"query":"FastAPI 요청 본문"}', f'call-{i}')]) for i in range(4)]
    client = FakeClient([*responses, completion('실제로 검색한 자료 [backend-1]')])
    result = agent.respond('FastAPI 요청 본문 학습 자료', client=client)
    assert result['tools'] == ['search_documents']
    assert result['sources'][0]['id'] == 'backend-1'
    assert result['trace'][-1]['status'] == 'budget_finalization'
    assert 'tools' not in client.requests[-1]
    assert sum(m['role']=='tool' for m in client.requests[-1]['messages']) == 4


def test_unmentioned_skill_does_not_quote_generic_development():
    result = compare_requirements('[지원자의 경험]\nPython으로 REST API를 개발한 경험이 있습니다. Java는 사용할 줄 모릅니다.\n[채용공고]\nPython 개발 경험\nJava 개발 경험\nKotlin 개발 경험')
    rows = result['requirements']
    assert rows[0]['status'] == '일치'
    assert rows[1]['user_evidence'] == ['Java는 사용할 줄 모릅니다.']
    assert rows[2]['user_evidence'] == []
    assert rows[2]['status'] == '정보 부족'
