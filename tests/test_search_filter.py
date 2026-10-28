import json
from types import SimpleNamespace

import pytest

from ai import agent, web_search as web


def hit(title, description="", url="https://www.wanted.co.kr/wd/123"):
    return {"title": title, "description": description, "url": url}


@pytest.mark.parametrize("url", [
    "https://job.incruit.com/jobdb_list/searchjob.asp?col=job_all&il=y&kw=Spring+boot",
    "https://job.incruit.com/JOBDB_LIST/SEARCHJOB.ASP?kw=Java",
    "https://job.incruit.com/jobdb_list/joblist.asp?cd=1",
])
def test_incruit_list_leak_from_deployment_is_excluded(url):
    results, excluded = web.filter_job_results([
        hit("Spring boot - 인크루트 채용정보", "Java Spring Boot 신입 백엔드", url)
    ], "Java Spring Boot 신입 백엔드")
    assert results == []
    assert excluded[0]["reason"] == "검색·목록 페이지"


def test_incruit_individual_post_is_preserved():
    url = "https://job.incruit.com/jobdb_info/jobpost.asp?job=202610280001"
    results, excluded = web.filter_job_results([
        hit("Java Spring Boot 신입 백엔드 개발자 채용", "신입 지원 가능", url)
    ], "Java Spring Boot 신입 백엔드")
    assert not excluded
    assert results[0]["url"] == url
    assert results[0]["match_status"] == "요약 기준 조건 일치"


@pytest.mark.parametrize("item", [
    hit("Java Spring Boot 신입 취업 집중반", url="https://fastcampus.co.kr/dev_online_javaspring"),
    hit("React 채용공고 100+건", url="https://kr.indeed.com/q-react-jobs.html"),
    hit("백엔드 채용", url="https://www.jobkorea.co.kr/Search/?stext=python"),
    hit("Python 개발자", url="https://m.saramin.co.kr/job-industry/job-list?cat_kewd=292"),
    hit("FastAPI 개발자", url="https://example.com/jobs/"),
    hit("공지사항", url="https://example.com/about"),
    hit("백엔드 개발자 채용 마감", "모집이 종료되었습니다."),
])
def test_courses_lists_and_closed_posts_are_excluded(item):
    results, excluded = web.filter_job_results([item], "백엔드")
    assert not results and len(excluded) == 1


def test_entry_title_does_not_override_experience_lower_bound():
    results, excluded = web.filter_job_results([hit("백엔드 신입 Python FastAPI 채용", "경력 1~5년")], "Python FastAPI 신입")
    assert not results and "경력 하한" in excluded[0]["reason"]


def test_missing_typescript_and_entry_evidence_stay_unknown():
    results, _ = web.filter_job_results([hit("React 주니어 개발자 채용")], "React TypeScript 신입")
    checks = {c["condition"]: c["status"] for c in results[0]["conditions"]}
    assert checks == {"React": "요약에 명시", "TypeScript": "정보 부족", "신입": "정보 부족"}
    assert results[0]["match_status"] == "추가 확인 필요"


def test_all_conditions_present_is_still_not_verified_open():
    results, _ = web.filter_job_results([hit("신입 백엔드 채용", "Python, FastAPI 사용")], "Python FastAPI 신입")
    assert results[0]["match_status"] == "요약 기준 조건 일치"
    assert results[0]["recruitment_status"] == "원문·현재 모집 상태 미확인"


def test_java_is_not_javascript():
    results, _ = web.filter_job_results([hit("신입 JavaScript 개발자 채용")], "Java 신입")
    assert results[0]["conditions"][0]["status"] == "정보 부족"


def test_future_deadline_field_is_not_closed_state():
    results, excluded = web.filter_job_results([hit("신입 Python 개발자", "모집 마감일: 2027-01-01, 접수 마감: 2027-01-01")], "Python 신입")
    assert results and not excluded


def test_optional_experience_is_not_required_lower_bound():
    results, excluded = web.filter_job_results([hit("신입 Python 개발자", "경력 2년 이상 우대")], "Python 신입")
    assert results and not excluded


def test_tracking_urls_deduplicate_and_keep_job_identifier():
    items = [hit("Python 개발자 채용", url="https://m.saramin.co.kr/job-search/view?rec_idx=7&utm_source=a&cn=x"),
             hit("Python 개발자 채용", url="https://m.saramin.co.kr/job-search/view?rec_idx=7&utm_source=b")]
    results, _ = web.filter_job_results(items, "Python")
    assert len(results) == 1
    assert results[0]["url"] == "https://m.saramin.co.kr/job-search/view?rec_idx=7"


@pytest.mark.parametrize("url", ["javascript:alert(1)", "https://user:password@example.com/job/1", "https://[invalid"])
def test_invalid_urls_are_never_exposed(url):
    results, _ = web.filter_job_results([hit("개발자 채용", url=url)], "Python")
    assert not results


def test_original_conditions_not_sent_to_search_provider(monkeypatch):
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-only")
    requests = []
    def get(*args, **kwargs):
        requests.append(kwargs)
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"web": {"results": [hit("React 개발자 채용")]}})
    monkeypatch.setattr(web.httpx, "get", get)
    output = web.search_live_jobs("React", requested_query="개인 경력 원문 TypeScript 신입")
    assert requests[0]["params"]["q"] == "React 채용 공고"
    assert {c["condition"] for c in output["results"][0]["conditions"]} == {"React", "TypeScript", "신입"}


def test_only_filtered_hits_enter_model_results_and_sources(monkeypatch):
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-only")
    items = [hit("Python 신입 채용", "FastAPI"), hit("Python 강의", url="https://fastcampus.co.kr/lesson")]
    monkeypatch.setattr(web.httpx, "get", lambda *a, **k: SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"web": {"results": items}}))
    output = agent.run_tool("search_live_jobs", {"query": "Python"}, message="Python FastAPI 신입")
    assert len(output["results"]) == 1 and output["excluded_count"] == 1
    assert output["results"][0]["match_status"] == "요약 기준 조건 일치"


def test_final_search_answer_cannot_promote_unverified_or_initial_docs():
    results, _ = web.filter_job_results([hit("React 주니어 개발자")], "React TypeScript 신입")
    output = {"results": results, "searched_at": "2026-10-28T10:00:00+09:00"}
    sources = {"backend-1": {"id": "backend-1", "url": "https://fastapi.tiangolo.com/"},
               "web-1-1": {"id": "web-1-1", "url": results[0]["url"]}}
    result = agent._finish("모집 중인 신입 TypeScript 공고입니다! [backend-1]", ["search_live_jobs"], sources, [], [output])
    assert "추가 확인 필요" in result["answer"] and "TypeScript: 정보 부족" in result["answer"]
    assert "모집 중인" not in result["answer"]
    assert [s["id"] for s in result["sources"]] == ["web-1-1"]


def test_uncited_initial_sources_do_not_appear():
    result = agent._finish("학습 참고 [backend-1]", ["search_documents"], {"backend-1": {"id": "backend-1"}, "job-KAKAO": {"id": "job-KAKAO"}}, [], [])
    assert result["sources"] == [{"id": "backend-1"}]


def test_empty_filtered_results_do_not_invent_posts():
    text = web.render_job_results([{"results": [], "excluded_count": 4}])
    assert "찾지 못했습니다" in text and "4건 제외" in text


@pytest.mark.parametrize("mode", ["native", "json"])
def test_both_agent_protocols_apply_filtered_output(monkeypatch, mode):
    monkeypatch.setenv("AGENT_TOOL_MODE", mode)
    results, _ = web.filter_job_results([hit("신입 Python 개발자", "FastAPI")], "Python FastAPI 신입")
    monkeypatch.setattr(agent, "search_live_jobs", lambda query, **kwargs: {"results": results, "searched_at": "test"})
    def completion(answer=None, calls=None):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=answer, tool_calls=calls))])
    tool = SimpleNamespace(id="c1", type="function", function=SimpleNamespace(name="search_live_jobs", arguments='{"query":"Python FastAPI 신입"}'))
    responses = iter([completion(calls=[tool]) if mode == "native" else completion(json.dumps({"calls": [{"name": "search_live_jobs", "arguments": {"query": "Python FastAPI 신입"}}]})), completion("확정 합격 공고!")])
    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: next(responses))))
    result = agent.respond("Python FastAPI 신입 공고", client=fake)
    assert "확정 합격" not in result["answer"]
    assert "요약 기준 조건 일치" in result["answer"]
    assert result["tools"] == ["search_live_jobs"]
    assert all(s["id"].startswith("web-") for s in result["sources"])
