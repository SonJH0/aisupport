"""공고 검색 3건·이미지 분석 3건의 실제 응답을 저장한다. 내용 자동 통과 없음."""
import argparse
import base64
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://ai-job-assistant-xewt.onrender.com'
CASES = [
    ('search-python', 'search', 'Python과 FastAPI를 사용하는 신입 백엔드 개발자 채용공고를 검색해 주세요.', None,
     'search_live_jobs 실행. 개별 후보 또는 없음 안내, 링크·요약 조건 확인 구분·모집 상태 미확인. 강의·목록을 개별 공고로 추천하지 않음.'),
    ('search-java', 'search', 'Java와 Spring Boot를 사용하는 신입 백엔드 개발자 채용공고를 검색해 주세요.', None,
     'search_live_jobs 실행. 개별 후보 또는 없음 안내, 링크·조건 구분·모집 미확인. 신입 미기재를 주니어라는 이유만으로 인정하지 않음.'),
    ('search-react', 'search', 'React와 TypeScript를 사용하는 신입 프론트엔드 개발자 채용공고를 검색해 주세요.', None,
     'search_live_jobs 실행. 개별 후보 또는 없음 안내, 링크·조건 구분·모집 미확인. 강의·목록 제외.'),
    ('image-clear', 'image', '이미지의 채용 요건을 읽고 제 경험과 비교해 주세요. 제 경험: Python 개발 1년, SQL 프로젝트 경험이 있습니다. AWS 경험은 이 글에 기재하지 않았습니다. 이미지에서 확인되는 회사명과 직무, 요건을 먼저 적고, 요건별 일치·차이·정보 부족과 근거를 구분해 주세요. 모르는 사실은 추측하지 마세요.',
     'image-01-clear.png', '이미지 직접 판독: SAMPLE LABS, Backend Developer, Busan. Python 최소 2년과 입력 1년은 차이, SQL 경험 일치, 우대 AWS는 정보 부족, 마감일 미제공. 가상 공고 구분.'),
    ('image-missing', 'image', '이미지의 회사명, 직무, 요구 기술을 읽어 주세요. 요구 경력 연수, 급여, 마감일도 알려 주되 이미지에 제공되지 않은 정보는 미확인으로 구분하세요. 추측하지 마세요.',
     'image-02-missing.png', '이미지 직접 판독: DEMO STUDIO, Frontend Developer, React·TypeScript. 경력 연수·급여·마감일은 미제공. 가상 공고 구분.'),
    ('image-not-job', 'image', '이 이미지에서 확인되는 자료의 종류와 주요 내용을 설명해 주세요. 채용공고인지 판단하고, 확인되지 않는 채용 직무·요건은 만들어내지 마세요.',
     'image-03-not-job.png', '이미지 직접 판독: DEMO CAFE 영수증. 아메리카노 2잔 8,000원·차 1잔 4,000원·합계 12,000원. 채용공고 아님, 채용 요건 창작 없음.'),
]

def payload_for(question, filename):
    payload = {'message': question, 'consent': True, 'history': []}
    metadata = None
    if filename:
        path = ROOT / 'docs/image-validation' / filename
        raw = path.read_bytes()
        if not raw.startswith(b'\x89PNG\r\n\x1a\n') or len(raw) > 4 * 1024 * 1024:
            raise ValueError('검증 PNG 형식 또는 크기를 확인하세요: ' + filename)
        metadata = {'path': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        payload['image'] = 'data:image/png;base64,' + base64.b64encode(raw).decode('ascii')
    return payload, metadata

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', nargs='+', choices=['search', 'image'], default=['search', 'image'])
    parser.add_argument('--dry-run', action='store_true', help='고정 질문·이미지 파일만 검사. 네트워크 호출 없음')
    args = parser.parse_args()
    selected = [case for case in CASES if case[1] in args.cases]
    prepared = [(case, *payload_for(case[2], case[3])) for case in selected]
    if args.dry_run:
        for case, payload, metadata in prepared:
            print(case[0], '입력 준비 확인', metadata or '(텍스트만)')
        print('실제 배포 요청·기능 검증은 실행하지 않았습니다.')
        return
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    folder = ROOT / 'docs/verification/search-image-evidence' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True)
    print('Saved:', folder.resolve(), flush=True)
    print('실제 AI 요청은 최대 6건입니다. 실패는 자동 재시도하지 않습니다.', flush=True)
    for (name, group, question, filename, expected), payload, metadata in prepared:
        record = {'case': name, 'group': group, 'question': question, 'expected': expected,
                  'review': '미판정', 'local_revision': revision, 'image': metadata,
                  'time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        started = time.monotonic()
        stop = False
        try:
            with urllib.request.urlopen(BASE + '/health', timeout=60) as response:
                record['health_before'] = json.load(response)
            if record['health_before'].get('revision') != revision:
                record['skipped'] = 'deployment_revision_mismatch'
                stop = True
            else:
                request = urllib.request.Request(BASE + '/api/chat', data=json.dumps(payload).encode(),
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
        record['elapsed_seconds'] = round(time.monotonic() - started, 2)
        (folder / (name + '.json')).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"{name}: HTTP={record.get('status')}; {record.get('skipped', record.get('error_type', '내용 검토 필요'))}", flush=True)
        if stop:
            print('배포 버전 불일치로 중단했습니다. 나머지는 실행하지 않았습니다.', flush=True)
            break
    print('Saved:', folder.resolve())
    print('HTTP 200은 내용 통과 판정이 아닙니다. 원문 답변·도구·trace를 검토하세요.')

if __name__ == '__main__':
    main()
