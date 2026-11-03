"""배포·고지·서버 동의 차단·동의 후 상담 1건을 확인하고 원본을 보존한다."""
import argparse
import datetime
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://ai-job-assistant-xewt.onrender.com'
QUESTION = 'Python으로 API 프로젝트를 만들었습니다. 취업 준비를 위해 제 역할과 구현 내용을 정리할 때 확인할 질문 2개를 알려주세요. 공고 검색은 하지 마세요.'

def fetch(path, payload=None, timeout=60):
    request = urllib.request.Request(BASE + path,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={} if payload is None else {'Content-Type': 'application/json'})
    started = time.monotonic()
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, response.headers.get('X-Request-ID'), response.read().decode('utf-8', errors='replace'), round(time.monotonic() - started, 2)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='실행 없이 입력만 확인')
    args = parser.parse_args()
    if args.dry_run:
        print('상태·화면·정적 파일·설정 파일 비공개·미동의 2건·동의 후 실제 상담 1건을 검사하도록 준비됐습니다. 네트워크 호출 없음.')
        return
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    folder = ROOT / 'docs/verification/final-operations-20261103' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True)
    print('Saved:', folder.resolve(), flush=True)
    checks = [
        ('health', '/health', None), ('page', '/', None), ('script', '/static/app.js', None),
        ('env-root', '/.env', None), ('env-static', '/static/.env', None),
        ('no-consent', '/api/chat', {'message': '동의 차단 확인용 질문', 'consent': False, 'history': []}),
        ('missing-consent', '/api/chat', {'message': '동의 차단 확인용 질문', 'history': []}),
        ('consented-chat', '/api/chat', {'message': QUESTION, 'consent': True, 'history': []}),
    ]
    for name, path, payload in checks:
        record = {'check': name, 'path': path, 'local_revision': revision, 'review': '미판정',
                  'time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        stop = False
        try:
            status, request_id, body, elapsed = fetch(path, payload, 210 if name == 'consented-chat' else 60)
            record.update(status=status, request_id=request_id, elapsed_seconds=elapsed)
            if name == 'health':
                record['response'] = json.loads(body)
                if status != 200 or record['response'].get('revision') != revision:
                    record['stopped'] = 'health_or_revision_mismatch'
                    stop = True
            elif name == 'page':
                tag = re.search(r'<input\b[^>]*\bid=["\']consent["\'][^>]*>', body, re.I)
                record['observations'] = {'ai_notice_text': 'AI가 생성한 참고 정보' in body,
                    'consent_checkbox_required': bool(tag and re.search(r'\brequired\b', tag.group(0))),
                    'limitation': 'HTML 문자열 확인이며 브라우저 렌더링·실제 클릭 검사가 아님'}
            elif name == 'script':
                record['observations'] = {'javascript_returned': status == 200 and '/api/chat' in body}
            elif name.startswith('env-'):
                # 설정 파일이 공개돼도 실제 값은 결과 파일·터미널에 남기지 않는다.
                record['observations'] = {'not_public_by_status': status in (403, 404), 'response_body_saved': False}
                if status not in (403, 404):
                    record['stopped'] = 'unexpected_configuration_path_response'
                    stop = True
            else:
                record['request'] = payload
                record['raw_response'] = body
                try:
                    record['response'] = json.loads(body)
                except ValueError:
                    record['response_format'] = 'not_json'
        except (OSError, TimeoutError, ValueError) as error:
            record['error_type'] = type(error).__name__
            stop = name == 'health'
        (folder / (name + '.json')).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"{name}: HTTP={record.get('status')}; {record.get('stopped', record.get('error_type', '내용 검토 필요'))}", flush=True)
        if stop:
            print('점검을 중단했습니다. 나머지 항목은 실행하지 않았습니다.', flush=True)
            break
    print('Saved:', folder.resolve())
    print('키 폐기·재발급·배포 설정·지속 가용성·모든 기능 통과를 이 실행으로 증명하지 않습니다.')

if __name__ == '__main__':
    main()
