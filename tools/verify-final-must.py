"""최신 배포의 Must 및 원래 평가 기능을 3회씩 기록한다. 내용 통과는 수동 검토한다."""
import argparse
import ast
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://ai-job-assistant-xewt.onrender.com'

def original_cases():
    tree = ast.parse((ROOT / 'tools/verify-reevaluation.py').read_text(encoding='utf-8'))
    return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'CASES' for t in n.targets))

def prepared_cases():
    spec = importlib.util.spec_from_file_location('image_cases', ROOT / 'tools/verify-search-images.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cases = []
    for name, (message, expected) in original_cases().items():
        for attempt in range(1, 4):
            cases.append((name, attempt, {'message': message, 'consent': True, 'history': []}, expected, None))
    for group in ['search', 'image']:
        for attempt, row in enumerate([r for r in module.CASES if r[1] == group], 1):
            payload, metadata = module.payload_for(row[2], row[3])
            cases.append((group, attempt, payload, row[4], metadata))
    return cases

def fetch(path, payload=None):
    request = urllib.request.Request(BASE + path, data=None if payload is None else json.dumps(payload).encode(), headers={} if payload is None else {'Content-Type': 'application/json'})
    try:
        response = urllib.request.urlopen(request, timeout=210 if payload and payload.get('consent') else 45)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        body = response.read().decode('utf-8', errors='replace')
        result = {'status': response.status, 'request_id': response.headers.get('X-Request-ID'), 'raw_response': body}
        try:
            result['response'] = json.loads(body)
        except ValueError:
            pass
        return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    cases = prepared_cases()
    if args.dry_run:
        print('AI 요청 18건: spec/role/chat/agent/search/image 각 3건. 동의 검사는 3회(미동의·누락 각각).')
        print('입력·이미지 준비 완료. 실제 요청·결과 저장 없음.')
        return
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    folder = ROOT / 'docs/verification/final-must' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True)
    manifest = {'local_revision': revision, 'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'planned_ai_requests': 18, 'review': '미판정', 'completed': [], 'stopped': None}
    (folder/'run.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Saved:', folder.resolve(), flush=True)
    checks = [('consent', n, {'message': '미동의 차단 확인', 'consent': False, 'history': []}, '403 동의 안내', None) for n in range(1,4)]
    checks += [('missing-consent', n, {'message': '동의 누락 차단 확인', 'history': []}, '403 동의 안내', None) for n in range(1,4)]
    checks += cases
    for name, attempt, payload, expected, image in checks:
        record = {'case': name, 'attempt': attempt, 'local_revision': revision, 'time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'request': {k:v for k,v in payload.items() if k != 'image'}, 'image': image, 'expected': expected, 'review': '미판정'}
        started = time.monotonic()
        stop = None
        try:
            health = fetch('/health')
            record['health_before'] = health
            if health['status'] != 200 or health.get('response', {}).get('revision') != revision:
                stop = 'health_or_revision_mismatch'
            else:
                if name == 'consent':
                    page = fetch('/')
                    body = page['raw_response']
                    record['page'] = {'status': page['status'], 'ai_notice': 'AI가 생성한 참고 정보' in body, 'required_consent': 'id="consent"' in body and 'required' in body, 'limitation': 'HTML 문자열 확인. 실제 브라우저 조작 아님'}
                record['result'] = fetch('/api/chat', payload)
        except (OSError, TimeoutError, ValueError) as error:
            record['error_type'] = type(error).__name__
            stop = 'transport_or_response_error'
        record['elapsed_seconds'] = round(time.monotonic()-started, 2)
        record['stopped'] = stop
        filename = f'{name}-{attempt}.json'
        (folder/filename).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        manifest['completed'].append(filename)
        manifest['stopped'] = stop
        (folder/'run.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"{name}-{attempt}: HTTP={record.get('result',{}).get('status')}; {stop or '내용 검토 필요'}", flush=True)
        if stop:
            print('중단. 남은 항목 미실행. 자동 재시도 없음.', flush=True)
            break
    print('Saved:', folder.resolve())
    print('HTTP 200은 내용 통과가 아닙니다. 답변·출처·도구·trace를 검토하세요.')

if __name__ == '__main__':
    main()
