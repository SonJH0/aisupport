"""실제 API 응답에서 발견한 루트 URL과 경험·숙련도 혼합의 회귀 검사."""
import json

import pytest
from ai import agent, web_search
from ai.comparison import compare_requirements
from test_agent_api import FakeClient, completion, call


def compare(experience, requirements):
    return compare_requirements('[지원자의 경험]\n'+experience+'\n[채용공고]\n'+requirements)['requirements']


@pytest.mark.parametrize('url', ['https://www.rallit.com', 'https://www.rallit.com/', 'https://www.rallit.com/?utm_source=test', 'https://jobs.example.com/?q=react'])
def test_platform_homepage_is_not_a_job(url):
    results, excluded = web_search.filter_job_results([{'title':'IT 인재 채용 플랫폼 - 랠릿', 'url':url}], 'React TypeScript 신입 프론트엔드')
    assert not results and excluded[0]['reason']=='홈페이지·개별 공고 근거 부족'


def test_rallit_homepage_removed_without_losing_individual_post():
    results, excluded = web_search.filter_job_results([
        {'title':'IT 인재 채용 플랫폼 - 랠릿','url':'https://www.rallit.com'},
        {'title':'React TypeScript 신입 프론트엔드 개발자 채용','url':'https://www.rallit.com/positions/1731/sample'}], 'React TypeScript 신입 프론트엔드')
    assert len(excluded)==1 and len(results)==1
    assert '/positions/1731/' in results[0]['url']


def test_personal_experience_does_not_require_unstated_proficiency():
    row = compare('개인 프로젝트에서 Python을 6개월 사용했습니다. 회사에서 근무한 경력은 없습니다.', 'Python 개발 경험')[0]
    assert row['experience_status']=='일치'
    assert row['proficiency_status'].startswith('미확인')
    assert '6개월' in row['user_evidence'][0]


def test_missing_operational_experience_does_not_negate_language_experience():
    row = compare('Python으로 REST API를 만들었습니다. 배포 경험은 없습니다.', 'Python API 개발 경험')[0]
    assert row['experience_status']=='일치'
    row = compare('Python으로 REST API를 만들었지만 배포 경험은 없습니다.', 'Python API 개발 경험')[0]
    assert row['experience_status']=='일치'


def test_absence_is_different_from_missing_information():
    rows = compare('Python으로 REST API를 만들었습니다. Java는 사용할 줄 모릅니다.', 'Python 개발 경험\nJava 개발 경험\nKotlin 개발 경험')
    assert [r['experience_status'] for r in rows]==['일치','차이','정보 부족']


def test_explicit_kotlin_absence():
    assert compare('Kotlin은 사용해 본 적이 없습니다.', 'Kotlin 개발 경험')[0]['experience_status']=='차이'


@pytest.mark.parametrize('experience', ['JavaScript로 화면을 만들었습니다.', 'Python을 배우고 싶습니다.', 'Python 경험이 없지는 않습니다.', 'Python 경험이 없습니다. Python으로 API를 만들었습니다.'])
def test_ambiguous_or_unrelated_experience_is_not_confirmed(experience):
    row=compare(experience, 'Python 개발 경험')[0]
    assert row.get('experience_status') != '일치'


def test_explicit_duration_requirement_is_not_reduced_to_experience_only():
    row=compare('Python을 6개월 사용했습니다.', 'Python 개발 경험 3년 이상')[0]
    assert 'experience_status' not in row
    assert row['status']=='관련 표현 있음; 의미 확인 필요'


@pytest.mark.parametrize('mode',['native','json'])
def test_user_comparison_does_not_inject_unrelated_saved_jobs(monkeypatch,mode):
    monkeypatch.setenv('AGENT_TOOL_MODE',mode)
    monkeypatch.setattr(agent,'search_documents',lambda *a:pytest.fail('입력 공고 비교에 초기 자료 검색 금지'))
    plan=completion(calls=[call('compare_requirements')]) if mode=='native' else completion('{"calls":[{"name":"compare_requirements","arguments":{}}]}')
    client=FakeClient([plan,completion('Python 경험은 일치하며 숙련도는 별도 확인이 필요합니다.')])
    output=agent.respond('[지원자의 경험]\nPython을 6개월 사용했습니다.\n[채용공고]\nPython 개발 경험',client=client)
    assert output['tools']==['compare_requirements'] and output['sources']==[]
    assert output['trace'][0]['status']=='skipped_user_comparison'
    if mode=='json':
        final=json.loads(client.requests[-1]['messages'][-1]['content'])
        assert final['initial_evidence']==[]
        assert final['tool_results'][0]['result']['requirements'][0]['experience_status']=='일치'
    else:
        payload=[m for m in client.requests[-1]['messages'] if m['role']=='tool'][0]
        assert json.loads(payload['content'])['requirements'][0]['experience_status']=='일치'
