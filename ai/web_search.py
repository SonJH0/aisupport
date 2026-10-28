"""Brave 검색에서 채용공고 후보를 조회한다."""
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
import httpx

def search_live_jobs(query):
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
    results = []
    for item in items:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", ""))
        if urlparse(url).scheme not in ("http", "https"):
            continue
        results.append({
            "title": str(item.get("title", ""))[:300],
            "url": url,
            "snippet": str(item.get("description", ""))[:600],
            "published": str(item.get("age", ""))[:100],
        })
    return {"searched_at": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds"),
            "note": "검색 결과 요약은 실제 공고 여부와 마감 상태를 보장하지 않습니다. 반드시 원문을 확인하세요.",
            "results": results[:10]}
