"""도구 없는 상담, 원치 않는 외부 검색, 실제 유출 목록의 회귀 검사."""
import json
from types import SimpleNamespace

import pytest

from ai import agent, web_search
from ai.errors import ServiceError
from test_agent_api import FakeClient, completion, call


def test_general_counseling_native_answer_does_not_force_json(monkeypatch):
    monkeypatch.setenv('AGENT_TOOL_MODE', 'auto')
    client = FakeClient([completion('희망 직무와 현재 경험을 알려주세요.')])
    result = agent.respond('취업 준비를 도와줘', client=client)
    assert result['answer'] == '희망 직무와 현재 경험을 알려주세요.'
    assert result['tools'] == [] and len(client.requests) == 1


def test_json_no_tool_plan_is_valid_for_intake_questions(monkeypatch):
    monkeypatch.setenv('AGENT_TOOL_MODE', 'json')
    client = FakeClient([completion('{"calls":[]}'), completion('관심 직무와 프로젝트 경험은 무엇인가요?')])
    result = agent.respond('희망 직무가 아직 정해지지 않았습니다. 공고 검색은 하지 말고, 제 상황을 파악할 질문부터 해주세요.', client=client)
    assert result['tools'] == []
    final_input = json.loads(client.requests[-1]['messages'][-1]['content'])
    assert final_input['tool_results'] == []
    assert '질문' in result['answer'] or '무엇' in result['answer']


def test_non_json_plan_for_general_counseling_falls_back_without_tools(monkeypatch):
    monkeypatch.setenv('AGENT_TOOL_MODE', 'json')
    client = FakeClient([completion('먼저 상황을 확인해야 합니다.'), completion('관심 있는 분야와 준비 기간을 알려주세요.')])
    result = agent.respond('취업 준비를 도와주세요.', client=client)
    assert result['tools'] == []
    assert any(t['status'] == 'invalid_plan_counseling_fallback' for t in result['trace'])
    assert result['answer'].startswith('관심')


@pytest.mark.parametrize('message', [
    '취업 준비를 도와줘',
    '희망 직무가 없어요. 공고 검색은 하지 말고 질문부터 해주세요.',
    '채용공고 검색하지 마세요.',
    '공고 추천은 필요 없어요. 상담만 해주세요.',
    "Don't search for jobs. Ask about my situation.",
    '[지원자의 경험]\nPython\n[채용공고]\nPython 개발 경험',
])
def test_external_search_requires_user_request(monkeypatch, message):
    monkeypatch.setattr(agent, 'search_live_jobs', lambda *a, **k: pytest.fail('외부 검색 실행 금지'))
    result = agent.run_tool('search_live_jobs', {'query': '개발자 신입'}, message=message)
    assert result['error_code'] == 'search_not_requested'


@pytest.mark.parametrize('mode', ['json', 'native'])
def test_unwanted_search_does_not_replace_counseling_with_job_renderer(monkeypatch, mode):
    monkeypatch.setenv('AGENT_TOOL_MODE', mode)
    monkeypatch.setattr(agent, 'search_live_jobs', lambda *a, **k: pytest.fail('외부 검색 실행 금지'))
    plan = completion(json.dumps({'calls': [{'name': 'search_live_jobs', 'arguments': {'query': '신입 개발자'}}]}))
    if mode == 'native':
        plan = completion(calls=[call('search_live_jobs', '{"query":"신입 개발자"}')])
    client = FakeClient([plan, completion('먼저 관심 직무와 준비 기간을 알려주세요.')])
    result = agent.respond('취업 준비를 도와줘', client=client)
    assert result['tools'] == []
    assert result['answer'].startswith('먼저')
    assert '공고 검색 결과입니다' not in result['answer']
    assert any(t['action'] == 'search_live_jobs' and t['status'] == 'error' for t in result['trace'])


def test_search_optout_does_not_disable_document_search(monkeypatch):
    monkeypatch.setenv('AGENT_TOOL_MODE', 'json')
    client = FakeClient([completion('{"calls":[{"name":"search_documents","arguments":{"query":"HTML 접근성"}}]}'), completion('MDN 자료 [frontend-1]')])
    result = agent.respond('공고 검색하지 말고 HTML 접근성 학습 자료를 알려주세요.', client=client)
    assert result['tools'] == ['search_documents']
    assert result['sources'][0]['id'] == 'frontend-1'


def test_valid_explicit_job_query_still_runs(monkeypatch):
    seen = []
    monkeypatch.setattr(agent, 'search_live_jobs', lambda query, **kw: seen.append(query) or {'results': []})
    output = agent.run_tool('search_live_jobs', {'query': 'Java Spring Boot 신입'}, message='Java와 Spring Boot 신입 공고를 검색해 주세요.')
    assert seen == ['Java Spring Boot 신입'] and 'error' not in output


def test_empty_plan_cannot_claim_required_job_search(monkeypatch):
    monkeypatch.setenv('AGENT_TOOL_MODE', 'json')
    with pytest.raises(ServiceError):
        agent.respond('Python 신입 공고를 검색해 주세요.', client=FakeClient([completion('{"calls":[]}')]))


def test_unhashable_tool_name_has_controlled_error(monkeypatch):
    monkeypatch.setenv('AGENT_TOOL_MODE', 'json')
    with pytest.raises(ServiceError):
        agent.respond('상담해 주세요.', client=FakeClient([completion('{"calls":[{"name":[],"arguments":{}}]}')]))


@pytest.mark.parametrize('url,title', [
    ('https://www.incu-career.kr/recruit', '신입 주니어 공개/수시 채용 공고 분석'),
    ('https://www.jobkorea.co.kr/Theme/it_developer', '전문 채용관 - IT 개발자 신입 경력 취업 정보 & 공고'),
    ('https://inthiswork.com/junior', '주니어경력 채용정보'),
    ('https://github.com/jojoldu/junior-recruit-scheduler', '주니어 개발자 채용 정보'),
    ('https://linkareer.com/list/recruit', '대기업 공기업 스타트업 채용 실시간 공고'),
])
def test_observed_aggregate_pages_are_excluded(url, title):
    result, excluded = web_search.filter_job_results([{'title': title, 'url': url}], '신입 백엔드')
    assert result == [] and len(excluded) == 1


@pytest.mark.parametrize('url', [
    'https://www.wanted.co.kr/wd/240271',
    'https://zighang.com/recruitment/a9d2a459-c4cb-4aff-8517-8e9c720ff063',
    'https://example.com/recruit/individual-123',
])
def test_individual_posts_remain_available(url):
    result, excluded = web_search.filter_job_results([{'title': 'Python FastAPI 신입 백엔드 개발자 채용', 'url': url}], 'Python FastAPI 신입 백엔드')
    assert len(result) == 1 and not excluded
