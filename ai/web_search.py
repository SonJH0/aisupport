"""Brave 검색에서 채용공고 후보를 조회한다."""
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
import httpx


# 검색 요약에서 확인할 기술명이다. 문서 RAG의 검색·선택 규칙과는 무관하다.
TECHNOLOGIES = {
    "Python": r"(?<![a-z0-9])python(?![a-z0-9])|파이썬",
    "FastAPI": r"(?<![a-z0-9])fast\s*api(?![a-z0-9])",
    "Java": r"(?<![a-z0-9])java(?![a-z0-9])|자바(?!스크립트)",
    "Spring Boot": r"spring[\s-]*boot|스프링\s*부트",
    "Kotlin": r"(?<![a-z0-9])kotlin(?![a-z0-9])|코틀린",
    "React": r"(?<![a-z0-9])react(?:\.js)?(?![a-z0-9])|리액트",
    "TypeScript": r"(?<![a-z0-9])typescript(?![a-z0-9])|타입스크립트",
    "JavaScript": r"(?<![a-z0-9])javascript(?![a-z0-9])|자바스크립트",
    "Node.js": r"(?<![a-z0-9])node\.?js(?![a-z0-9])|노드\s*제이에스",
    "Django": r"(?<![a-z0-9])django(?![a-z0-9])|장고",
    "SQL": r"(?<![a-z0-9])sql(?![a-z0-9])",
}


def _text(value):
    # 검색 서비스가 넣은 강조 태그도 단순 텍스트로 처리한다.
    import html
    return re.sub(r"<[^>]*>", " ", html.unescape(str(value or "")))


def _canonical_url(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            return None
        # 같은 공고를 추적용 파라미터만 바꾸어 중복 노출하지 않는다.
        query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
                 if not k.lower().startswith(("utm_", "t_")) and k.lower() not in
                 {"ref", "referer", "referrer", "source", "cn", "cns", "client_id", "tracking"}]
        return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), "", urlencode(query), ""))
    except ValueError:
        return None


def _page_type(title, url):
    host = urlparse(url).hostname or ""
    path = urlparse(url).path.lower()
    # 채용 정보 모음·테마·저장소는 개별 회사 공고와 구분한다.
    if host in ("github.com", "www.github.com") and not re.search(r"/issues/\d+$", path):
        return "채용 정보 모음·저장소"
    if re.search(r"/(?:theme|list)(?:/|$)|/(?:recruit|junior)/?$", path):
        return "검색·목록 페이지"
    if re.search(r"채용\s*(?:공고\s*)?(?:모음|일정|정보\s*모음)|공개\s*/\s*수시\s*채용\s*공고\s*분석", title):
        return "채용 정보 모음·저장소"
    # 인크루트의 검색·목록 경로는 /search/ 형태가 아닌 ASP 주소를 사용한다.
    # 도메인 전체를 차단하면 개별 공고(jobdb_info/jobpost.asp)까지 사라진다.
    if (host == "incruit.com" or host.endswith(".incruit.com")) and (
        path == "/jobdb_list" or path.startswith("/jobdb_list/")
    ):
        return "검색·목록 페이지"
    if re.search(r"fastcampus|inflearn|udemy|coursera|wanted\.co\.kr/events", host + path):
        return "강의·교육 페이지"
    if re.search(r"강의|부트캠프|취업\s*집중반|교육생\s*모집|수강|튜토리얼|온라인\s*교육", title):
        return "강의·교육 페이지"
    if re.search(r"/blog(?:/|$)|/articles?(?:/|$)|/tutorials?(?:/|$)|/docs(?:/|$)|/courses?(?:/|$)", path):
        return "학습·기사 페이지"
    if re.search(r"/search(?:/|$)|/job-industry/|/jobs/?$|/positions/?$|/recruitments?/?$|/careers/?$|/q-", path):
        return "검색·목록 페이지"
    if re.search(r"검색\s*결과|검색결과|채용공고\s*\d+\+?\s*건|직업별\s*채용정보|취업\s*\|", title):
        return "검색·목록 페이지"
    if not re.search(r"채용|구인|모집|개발자|엔지니어|developer|engineer|hiring", title, re.I):
        return "개별 공고 근거 부족"
    return None


def _conditions(title, snippet, requested_query):
    text = title + "\n" + snippet
    checks = []
    for name, pattern in {"백엔드": r"백엔드|백\s*엔드|backend|back[ -]end|서버\s*개발|서버\s*엔지니어",
                          "프론트엔드": r"프론트\s*엔드|frontend|front[ -]end"}.items():
        if re.search(pattern, requested_query, re.I):
            found = re.search(pattern, text, re.I)
            checks.append({"condition": name, "status": "요약에 명시" if found else "정보 부족",
                           "evidence": found.group(0) if found else "검색 요약에 직무명 없음"})
    for name, pattern in TECHNOLOGIES.items():
        if re.search(pattern, requested_query, re.I):
            found = re.search(pattern, text, re.I)
            checks.append({"condition": name, "status": "요약에 명시" if found else "정보 부족",
                           "evidence": found.group(0) if found else "검색 요약에 기술명 없음"})
    if re.search(r"신입|new\s*grad|entry[ -]?level", requested_query, re.I):
        # 제목의 '신입'보다 경력 하한을 우선한다. '주니어'만으로 신입을 인정하지 않는다.
        required = re.search(r"(?:경력\s*[:：]?\s*)?([1-9]\d*)\s*(?:[~∼–-]\s*\d+\s*)?년\s*(?:이상|이내|경력|차|부터)|경력\s*[:：]?\s*([1-9]\d*)\s*(?:[~∼–-]\s*\d+\s*)?년", text)
        if required and not re.match(r"\s*(?:우대|선호)", text[required.end():]):
            return checks + [{"condition": "신입", "status": "조건 충돌", "evidence": required.group(0)}]
        entry = re.search(r"신입|경력\s*무관|경력\s*없어도|new\s*grad|entry[ -]?level|경력\s*0\s*(?:[~∼–-]\s*\d+\s*)?년", text, re.I)
        checks.append({"condition": "신입", "status": "요약에 명시" if entry else "정보 부족",
                       "evidence": entry.group(0) if entry else "신입 가능 여부 미기재(주니어만으로 인정하지 않음)"})
    return checks


def filter_job_results(items, requested_query):
    results, excluded, seen = [], [], set()
    for item in items:
        if not isinstance(item, dict):
            continue
        url = _canonical_url(str(item.get("url", "")))
        if not url:
            continue
        title = _text(item.get("title"))[:300]
        snippet = _text(item.get("description", item.get("snippet", "")))[:600]
        reason = _page_type(title, url)
        if not reason and re.search(r"(?:채용|모집)\s*마감(?:됨|되었습니다|입니다|\s*$|[.!。])|(?:채용|모집)(?:이|가)?\s*종료(?:됨|되었습니다|입니다|\s*$|[.!。])|position\s+(?:is\s+)?closed", title + "\n" + snippet, re.I):
            reason = "검색 요약에 마감·종료 명시"
        checks = _conditions(title, snippet, requested_query)
        if not reason and any(c["status"] == "조건 충돌" for c in checks):
            reason = "신입 요청과 경력 하한 충돌"
        if url in seen:
            continue
        seen.add(url)
        if reason:
            excluded.append({"title": title, "reason": reason})
            continue
        matched = bool(checks) and all(c["status"] == "요약에 명시" for c in checks)
        results.append({"title": title, "url": url, "snippet": snippet,
                        "published": str(item.get("age", item.get("published", "")))[:100],
                        "match_status": "요약 기준 조건 일치" if matched else "추가 확인 필요",
                        "conditions": checks, "recruitment_status": "원문·현재 모집 상태 미확인",
                        "note": ("요약 기준 조건 일치" if matched else "추가 확인 필요") + "; 원문·현재 모집 상태 미확인"})
    results.sort(key=lambda r: r["match_status"] != "요약 기준 조건 일치")
    return results, excluded


def render_job_results(outputs):
    """모델이 조건 미확인을 확정 추천으로 바꾸지 않도록 검색 결과를 직접 표시한다."""
    lines = ["공고 검색 결과입니다. 검색 요약 기준이며 원문과 현재 모집 여부는 확인하지 않았습니다."]
    seen = set()
    for output in outputs:
        if output.get("error"):
            lines.append(output["error"])
            continue
        lines.append("\n검색 시각: " + str(output.get("searched_at", "미확인")))
        for group in ("요약 기준 조건 일치", "추가 확인 필요"):
            hits = [h for h in output.get("results", []) if h.get("match_status") == group and h["url"] not in seen]
            if not hits:
                continue
            lines.append("\n[" + group + "]")
            for hit in hits:
                seen.add(hit["url"])
                lines.extend(["- " + hit["title"], hit["url"]])
                for check in hit.get("conditions", []):
                    lines.append("  " + check["condition"] + ": " + check["status"] + " — " + check["evidence"])
        if not output.get("results"):
            lines.append("조건을 확인할 수 있는 개별 공고 후보를 찾지 못했습니다. 검색어나 지역을 바꾸어 다시 시도해 주세요.")
        if output.get("excluded_count"):
            lines.append("\n강의·목록·마감·조건 충돌 등의 결과 " + str(output["excluded_count"]) + "건 제외.")
    lines.append("\n각 원문에서 기술 요건, 신입 지원 가능 여부, 지역, 기타 지원 조건, 모집 상태와 마감일을 확인하세요. 기술명 언급은 필수 요건 충족을 보장하지 않습니다.")
    return "\n".join(lines)

def search_live_jobs(query, *, requested_query=None):
    key = os.getenv("BRAVE_SEARCH_API_KEY", "").strip()
    if not key or key.startswith("여기에_"):
        return {"error": "실시간 검색이 설정되지 않았습니다. Brave 검색 API 키가 필요합니다.", "results": []}
    query = str(query).strip()
    if re.search(r"@|https?://|\d{3}[-. ]?\d{3,4}[-. ]?\d{4}|\d{6}[- ]?\d{7}", query, re.I):
        return {"error": "검색어에 개인정보나 링크를 포함할 수 없습니다. 직무·기술·지역만 입력하세요.", "results": []}
    if not query or len(query) > 120:
        return {"error": "검색어는 직무·기술·희망 지역만 포함하여 120자 이내로 입력하세요.", "results": []}
    try:
        response = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"Accept": "application/json", "X-Subscription-Token": key},
            params={"q": query + " 채용 공고", "country": "KR", "search_lang": "ko", "count": 10},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        return {"error": "실시간 검색에 실패했습니다. 검색 서비스 설정과 연결을 확인해 주세요.", "results": []}
    web = payload.get("web", {}) if isinstance(payload, dict) else {}
    items = web.get("results", []) if isinstance(web, dict) else []
    if not isinstance(items, list):
        return {"error": "검색 결과 형식이 올바르지 않습니다.", "results": []}
    # 사용자 원문은 로컬 조건 판정에만 사용하며 검색 서비스에는 위 query만 전송한다.
    results, excluded = filter_job_results(items, (requested_query or "") + " " + query)
    return {"searched_at": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds"),
            "note": "검색 요약 기준의 후보입니다. 조건 일치와 추가 확인 필요를 구분하고 원문·모집 상태 미확인을 알리세요.",
            "excluded_count": len(excluded), "excluded": excluded,
            "results": results[:10]}

