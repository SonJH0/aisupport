"""실제 배포 기능 12회: HTTP 성공을 내용 통과로 자동 판정하지 않는다."""
import datetime
import json
from pathlib import Path
import urllib.request
import urllib.error

BASE = 'https://ai-job-assistant-xewt.onrender.com'
CASES = {
    'spec': ('Python으로 REST API 프로젝트를 만들었습니다. SQL로 조회 기능을 구현했습니다. 제 스펙의 강점과 정보가 부족한 부분을 구분해 분석해 주세요. 공고 검색은 하지 마세요.', '입력 경험에 근거한 강점·정보 부족, 경력 창작 없음'),
    'role': ('Python REST API와 SQL 프로젝트 경험이 있습니다. 개발 직무 후보 2개와 제 경험에 근거한 이유, 더 확인할 질문을 제안해 주세요. 채용공고 검색은 하지 마세요.', '직무 후보·경험 근거·추가 질문, 공고 목록으로 대체하지 않음'),
    'chat': ('FastAPI 요청 본문 검증을 배우려면 어떤 자료를 참고하나요? 출처와 학습 순서를 알려주세요.', '실제 검색 본문과 연결된 출처·학습 조언'),
    'agent': ('[지원자의 경험]\nPython으로 REST API를 개발한 경험이 있습니다. Java는 사용할 줄 모릅니다.\n[채용공고]\nPython 개발 경험\nJava 개발 경험\nKotlin 개발 경험\n', 'compare_requirements 실행, Python 일치·Java 차이·Kotlin 정보 부족 및 조언 일관성'),
}
folder = Path('docs/verification/reevaluation') / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
folder.mkdir(parents=True, exist_ok=True)
for name, (message, expected) in CASES.items():
    for attempt in range(1, 4):
        record = {'case': name, 'attempt': attempt, 'expected': expected, 'review': '미판정', 'message': message, 'time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        try:
            request = urllib.request.Request(BASE + '/api/chat', data=json.dumps({'message':message, 'consent':True, 'history':[]}).encode(), headers={'Content-Type':'application/json'})
            try:
                response = urllib.request.urlopen(request, timeout=210)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                record.update(status=response.status, request_id=response.headers.get('X-Request-ID'), response=response.read().decode('utf-8', errors='replace'))
        except (OSError, TimeoutError) as error:
            record.update(status=None, error_type=type(error).__name__)
        (folder / f'{name}-{attempt}.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'{name}-{attempt}: HTTP {record.get("status")}; 내용 검토 필요', flush=True)
print('Saved:', folder.resolve())
