"""고정 학습 질문 3개의 로컬 검색 본문과 선택적 실제 배포 응답을 보존한다."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ai.retrieval import search_documents

BASE = 'https://ai-job-assistant-xewt.onrender.com'
CASES = {
    'fastapi': 'FastAPI 요청 본문과 입력 검증을 배우려면 어떤 자료를 참고하나요? 검색 자료의 내용과 추가 실습 제안을 구분하고 문단 ID와 출처를 알려주세요.',
    'html': 'HTML 폼 구조와 접근성을 배우려면 어떤 자료를 참고하나요? 검색 자료의 내용과 추가 실습 제안을 구분하고 문단 ID와 출처를 알려주세요.',
    'pandas': 'pandas에서 여러 표 결합과 요약 통계를 배우려면 어떤 자료를 참고하나요? 검색 자료의 내용과 추가 실습 제안을 구분하고 문단 ID와 출처를 알려주세요.',
}

def get_health():
    with urllib.request.urlopen(BASE + '/health', timeout=60) as response:
        return json.load(response)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local-only', action='store_true', help='로컬 검색만 기록. 실제 AI 호출 없음')
    args = parser.parse_args()
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    folder = ROOT / 'docs/verification/rag-evidence' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True)
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
              for name in ('ai/retrieval.py', 'ai/agent.py', 'data/knowledge.json', 'data/jobs.json')}
    for name, question in CASES.items():
        record = {'case': name, 'question': question, 'local_revision': revision,
                  'local_file_sha256': hashes, 'local_retrieval': search_documents(question),
                  'review': '미판정', 'time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'scope': 'local_only' if args.local_only else 'local_retrieval_and_live_response'}
        if not args.local_only:
            try:
                record['health_before'] = get_health()
                if record['health_before'].get('revision') != revision:
                    record['skipped'] = 'deployment_revision_mismatch'
                else:
                    request = urllib.request.Request(BASE + '/api/chat', data=json.dumps({
                        'message': question, 'consent': True, 'history': []}).encode(),
                        headers={'Content-Type': 'application/json'})
                    try:
                        response = urllib.request.urlopen(request, timeout=210)
                    except urllib.error.HTTPError as error:
                        response = error
                    with response:
                        body = response.read().decode('utf-8', errors='replace')
                        record.update(status=response.status, request_id=response.headers.get('X-Request-ID'), raw_response=body)
                        try:
                            record['response'] = json.loads(body)
                        except ValueError:
                            record['response_format'] = 'not_json'
            except (OSError, TimeoutError, ValueError) as error:
                record['error_type'] = type(error).__name__
        (folder / (name + '.json')).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"{name}: local IDs={[d['id'] for d in record['local_retrieval']]}; HTTP={record.get('status')}; {record.get('skipped', record.get('error_type', '내용은 수동 검토'))}", flush=True)
    print('Saved:', folder.resolve())
    print('로컬 검색은 서버 프롬프트 캡처가 아니며 HTTP 200은 내용 통과 판정이 아닙니다.')

if __name__ == '__main__':
    main()
