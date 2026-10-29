"""Save synthetic public-API responses for human review; never auto-claim G4 success."""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://ai-job-assistant-xewt.onrender.com/api/chat"
KST = timezone(timedelta(hours=9))
CASES = [
    ("rag-01", "백엔드 API의 요청 본문과 입력 검증을 배우려면 어떤 자료를 참고해야 하나요? 관련 자료의 출처와 함께 학습 방향을 알려주세요.", "FastAPI 문단·공식 링크·학습 조언"),
    ("rag-02", "프론트엔드에서 HTML 폼과 웹 접근성을 배우려면 어떤 자료를 참고해야 하나요? 관련 자료의 출처와 함께 학습 방향을 알려주세요.", "MDN 문단·공식 링크·학습 조언"),
    ("rag-03", "Python pandas로 표 데이터를 읽고, 두 표를 결합하고, 요약 통계를 구하는 방법을 배우려면 어떤 자료를 참고해야 하나요? 관련 자료의 출처와 함께 학습 방향을 알려주세요.", "pandas 문단·공식 링크·학습 조언"),
    ("search-02", "Java와 Spring Boot를 사용하는 신입 백엔드 개발자 채용공고를 검색해 주세요.", "개별 공고 또는 없음 안내·조건 구분·모집 미확인·링크·목록 제외"),
    ("search-03", "React와 TypeScript를 사용하는 신입 프론트엔드 개발자 채용공고를 검색해 주세요.", "개별 공고 또는 없음 안내·조건 구분·모집 미확인·링크·목록 제외"),
    ("compare-01", "아래 채용공고와 지원자 경험을 비교해 일치·차이·정보 부족, 확인 질문과 보완 행동을 알려주세요.\n[지원자의 경험]\nPython으로 REST API를 만들었습니다. Java로 게시판 프로젝트를 만들었습니다. Kotlin은 사용해 본 적이 없습니다.\n[채용공고]\nPython API 개발 경험\nJava 개발 경험\nKotlin 개발 경험", "Python·Java 일치, Kotlin 차이, 근거·확인 질문·보완 행동; 숙련도는 미확인"),
    ("compare-02", "아래 채용공고와 지원자 경험을 비교해 일치·차이·정보 부족, 확인 질문과 보완 행동을 알려주세요.\n[지원자의 경험]\nPython으로 REST API를 개발한 경험이 있습니다. Java는 사용할 줄 모릅니다.\n[채용공고]\nPython 개발 경험\nJava 개발 경험\nKotlin 개발 경험", "Python 일치·Java 차이·Kotlin 정보 부족, 근거·확인 질문·보완 행동"),
    ("compare-03", "아래 채용공고와 지원자 경험을 비교해 일치·차이·정보 부족, 확인 질문과 보완 행동을 알려주세요.\n[지원자의 경험]\n개인 프로젝트에서 Python을 6개월 사용했습니다. 회사에서 근무한 경력은 없습니다.\n[채용공고]\n회사 근무 경력 1년 이상\nPython 개발 경험\nSQL 사용 경험", "회사 경력 차이·Python 경험 일치(숙련도미확인)·SQL 정보 부족, 근거·질문·보완 행동"),
]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', nargs='+', choices=[c[0] for c in CASES],
                        help='Run only these cases; omitted means all eight.')
    args = parser.parse_args(argv)
    selected = [case for case in CASES if not args.cases or case[0] in args.cases]
    run_id = datetime.now(KST).strftime("%Y%m%d-%H%M%S")
    output = ROOT / "docs" / "verification" / "final-text-api" / run_id
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for label, message, expected in selected:
        body = {"message": message, "consent": True, "history": []}
        record = {"id": label, "started_at": datetime.now(KST).isoformat(),
                  "endpoint": ENDPOINT, "synthetic_technical_test": True,
                  "real_user_feedback": False, "request": body,
                  "expected_for_human_review": expected,
                  "deployment_sha": "not_observed_by_this_script",
                  "human_verdict": "미판정"}
        request = Request(ENDPOINT, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                          headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=210) as response:
                record["http_status"] = response.status
                record["response"] = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            record["http_status"] = error.code
            # 오류 HTML의 내장 글꼴이 앞부분을 채워도 본문을 보존하도록 한도를 늘린다.
            raw_error = error.read(1000001)
            record["error_body"] = raw_error[:1000000].decode("utf-8", errors="replace")
            record["error_body_truncated"] = len(raw_error) > 1000000
        except (URLError, TimeoutError, OSError, ValueError) as error:
            record["http_status"] = None
            record["error"] = str(error)
        record["finished_at"] = datetime.now(KST).isoformat()
        (output / f"{label}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        rows.append(record)
        tools = record.get("response", {}).get("tools", [])
        print(f"{label}: HTTP {record['http_status']}; tools={tools}; review required", flush=True)
    review = "# Synthetic API responses for human review\n\n"
    review += "HTTP status is not a functional success verdict. Runtime commit SHA was not observed by this script.\n\n"
    review += "| Case | HTTP | Response | Human verdict |\n|---|---|---|---|\n"
    for row in rows:
        review += f"| {row['id']} | {row['http_status']} | [{row['id']}.json]({row['id']}.json) | Review required |\n"
    (output / "README.md").write_text(review, encoding="utf-8")
    print(f"Saved: {output}", flush=True)
    return 0 if all(r["http_status"] == 200 for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())

