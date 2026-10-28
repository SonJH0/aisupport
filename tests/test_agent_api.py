import copy
import json
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient

import ai.agent as agent
import ai.vision as vision
import ai.web_search as web
import backend.main as api
from ai.comparison import compare_requirements
from ai.errors import ServiceError
from ai.retrieval import rank_documents, search_documents


def completion(answer=None, calls=None):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=answer, tool_calls=calls))])


def call(name, arguments='{}', ident='call-1'):
    return SimpleNamespace(id=ident, type='function', function=SimpleNamespace(name=name, arguments=arguments))


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
    def create(self, **kwargs):
        self.requests.append(copy.deepcopy(kwargs))
        return next(self.responses)


@pytest.mark.parametrize('query,expected', [
    ('백엔드 추천', 'backend'), ('API 요청 본문 입력 검증', 'backend'),
    ('프론트엔드 레이아웃 접근성', 'frontend'), ('HTML 폼 구조 링크', 'frontend'),
    ('pandas DataFrame 그래프', 'data'), ('데이터 분석 표 결합 통계', 'data')])
def test_retrieval_finds_body_paragraphs(query, expected):
    hits = search_documents(query)
    assert hits
    expected_title = {'backend': '백엔드', 'frontend': '프론트엔드', 'data': '데이터 분석'}[expected]
    assert expected_title in hits[0]['title']
    assert all(h['score'] >= 0.15 for h in hits)
    assert not any('SAMPLE' in h['id'] for h in hits)


@pytest.mark.parametrize('query', ['', 'zzzzzz', '오늘 점심은 무엇을 먹을까'])
def test_unknown_query_does_not_get_fixed_job(query):
    assert search_documents(query) == []


def test_new_document_body_is_searchable_without_editing_keywords():
    docs = [{'id':'a','title':'문서 A','text':'고유검색어쿼카테스트 새로운 본문'},
            {'id':'b','title':'문서 B','text':'다른 내용'}]
    assert rank_documents('고유검색어쿼카테스트', docs)[0]['id'] == 'a'


def test_native_tool_call_roundtrip():
    client = FakeClient([completion(calls=[call('search_documents','{"query":"백엔드 API"}')]), completion('답변 [backend-1]')])
    result = agent.respond('백엔드 API 학습', client=client)
    assert result['tools'] == ['search_documents']
    assert result['trace'][0]['action'] == 'initial_retrieval'
    tool_message = [m for m in client.requests[1]['messages'] if m['role']=='tool'][0]
    assert tool_message['tool_call_id'] == 'call-1'
    assert json.loads(tool_message['content'])['documents']
    assert len(client.requests[0]['tools']) == 4
    assert 'tool_choice' not in client.requests[0]
    assert result['sources']


def test_compare_uses_original_user_input():
    message = '[지원자의 경험]\nPython을 못합니다. HTML 화면을 만들었습니다.\n[채용공고]\nPython 개발\nKotlin 개발'
    client = FakeClient([completion(calls=[call('compare_requirements')]), completion('확인이 필요합니다.')])
    result = agent.respond(message, client=client)
    tool_output = json.loads([m for m in client.requests[1]['messages'] if m['role']=='tool'][0]['content'])
    assert '못합니다' in tool_output['requirements'][0]['user_evidence'][0]
    assert tool_output['requirements'][1]['status'] == '정보 부족'
    assert result['tools'] == ['compare_requirements']


def test_compare_missing_fields_requests_input():
    assert compare_requirements('검토해 주세요')['status'] == 'needs_input'


@pytest.mark.parametrize('name,args', [('delete_files',{}), ('search_documents',{'query':1}),
    ('search_documents',{'query':'a','extra':'x'}), ('compare_requirements',{'experience':'invented'}),
    ('search_documents',[]), ('get_job',{'job_id':''})])
def test_invalid_tool_arguments_are_rejected(name,args):
    assert 'error' in agent.run_tool(name,args)


def test_bad_json_is_returned_to_model_without_crash():
    client=FakeClient([completion(calls=[call('search_documents','not-json')]),completion('다시 입력해 주세요.')])
    result=agent.respond('백엔드',client=client)
    assert result['trace'][-1]['status']=='error'
    assert result['tools']==[]


def test_multiple_calls_get_matching_results():
    client=FakeClient([completion(calls=[call('search_documents','{"query":"백엔드"}','a'),call('get_job','{"job_id":"SAMPLE-1"}','b')]),completion('가상 공고 예시입니다.')])
    result=agent.respond('백엔드와 SAMPLE-1',client=client)
    assert result['tools']==['search_documents','get_job']
    assert [m['tool_call_id'] for m in client.requests[1]['messages'] if m['role']=='tool']==['a','b']


def test_repeated_calls_stop_at_budget():
    client=FakeClient([completion(calls=[call('get_job','{"job_id":"SAMPLE-1"}')]) for _ in range(4)])
    with pytest.raises(ServiceError):agent.respond('SAMPLE-1',client=client)
    assert len(client.requests)==4


def test_empty_answer_is_controlled_error():
    with pytest.raises(ServiceError):agent.respond('백엔드',client=FakeClient([completion('')]))


def test_missing_key_is_controlled(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    monkeypatch.delenv('CODYSSEY_API_KEY',raising=False)
    with pytest.raises(ServiceError) as caught:agent.create_client()
    assert caught.value.status_code==503


def test_missing_web_key_is_not_success(monkeypatch):
    monkeypatch.delenv('BRAVE_SEARCH_API_KEY',raising=False)
    result=web.search_live_jobs('백엔드')
    assert result['results']==[] and 'error' in result


@pytest.mark.parametrize('query',['test@example.com','010-1234-5678','https://example.com','x'*121])
def test_sensitive_or_oversized_web_query_is_blocked(monkeypatch,query):
    monkeypatch.setenv('BRAVE_SEARCH_API_KEY','test-only')
    monkeypatch.setattr(web.httpx,'get',lambda *a,**kw:pytest.fail('must not send'))
    assert 'error' in web.search_live_jobs(query)


@pytest.mark.parametrize('data',['broken','data:text/html;base64,YQ==','data:image/png;base64,@@@'])
def test_invalid_image_rejected(monkeypatch,data):
    monkeypatch.setenv('ANTHROPIC_API_KEY','test-only')
    monkeypatch.setattr(vision.httpx,'post',lambda *a,**kw:pytest.fail('must not send'))
    with pytest.raises(ValueError):vision.analyze_image('공고',data)


@pytest.fixture
def client():return TestClient(api.app)


def test_app_boots_and_serves_frontend(client):
    assert client.get('/health').json()['version']=='0.3.0'
    assert client.get('/').status_code==200
    assert client.get('/static/app.js').status_code==200


def test_backend_blocks_missing_consent(client,monkeypatch):
    monkeypatch.setattr(api,'respond',lambda *a,**kw:pytest.fail('must not call AI'))
    assert client.post('/api/chat',json={'message':'백엔드'}).status_code==403


@pytest.mark.parametrize('body',[{'message':'  ','consent':True},{'message':'x'*10001,'consent':True},
    {'message':'a','consent':True,'history':[{'role':'system','content':'bad'}]}])
def test_input_validation(client,body):assert client.post('/api/chat',json=body).status_code==422


def test_api_returns_existing_contract_and_trace(client,monkeypatch):
    expected={'answer':'답변','tools':['search_documents'],'sources':[],'trace':[],'ai_generated':True}
    monkeypatch.setattr(api,'respond',lambda *a,**kw:expected)
    assert client.post('/api/chat',json={'message':'백엔드','consent':True}).json()==expected


def test_service_error_is_sanitized(client,monkeypatch):
    def fail(*a,**kw):raise ServiceError('키 설정 필요',503)
    monkeypatch.setattr(api,'respond',fail)
    assert client.post('/api/chat',json={'message':'a','consent':True}).status_code==503


def test_gateway_unsupported_native_uses_real_json_plan(monkeypatch):
    from openai import BadRequestError
    request = httpx.Request('POST','https://example.org/v1/chat/completions')
    response = httpx.Response(400,request=request)
    error = BadRequestError('Requested feature is not supported.',response=response,body={})
    client=FakeClient([])
    answers=iter([error,completion('{"calls":[{"name":"compare_requirements","arguments":{}}]}'),completion('Python은 확인 필요, Kotlin은 정보 부족입니다.')])
    def create(**kwargs):
        client.requests.append(copy.deepcopy(kwargs))
        answer=next(answers)
        if isinstance(answer,Exception):raise answer
        return answer
    client.chat.completions.create=create
    monkeypatch.setenv('AGENT_TOOL_MODE','auto')
    result=agent.respond('[지원자의 경험]\nPython 못함\n[채용공고]\nPython 개발\nKotlin 개발',client=client)
    assert result['tools']==['compare_requirements']
    assert result['trace'][1]['status']=='native_unsupported_json_plan'
    assert 'tools' in client.requests[0] and 'tools' not in client.requests[1]
    final=json.loads(client.requests[-1]['messages'][-1]['content'])
    assert final['tool_results'][0]['result']['requirements']


def test_json_plan_cannot_inject_tool(monkeypatch):
    monkeypatch.setenv('AGENT_TOOL_MODE','json')
    client=FakeClient([completion('{"calls":[{"name":"delete_files","arguments":{}}]}')])
    with pytest.raises(ServiceError):agent.respond('백엔드',client=client)


def test_auto_no_native_call_still_executes_model_selected_tool(monkeypatch):
    monkeypatch.setenv('AGENT_TOOL_MODE','auto')
    client=FakeClient([completion('도구 없이 답변'),completion('{"calls":[{"name":"search_documents","arguments":{"query":"백엔드 API"}}]}'),completion('검색 자료 기반 답변')])
    result=agent.respond('백엔드 API',client=client)
    assert result['tools']==['search_documents']
    assert result['trace'][1]['status']=='native_no_tool_json_plan'
