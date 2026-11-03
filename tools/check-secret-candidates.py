import subprocess,json,re,datetime
from pathlib import Path
r=Path(__file__).resolve().parents[1]
def git(*args):return subprocess.check_output(['git',*args],cwd=r)
patterns={
 'provider_key_shape':re.compile(rb'(?<![A-Za-z0-9])(?:sk[-_]|BSA)[A-Za-z0-9_-]{20,}'),
 'private_key_header':re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
 'literal_secret_assignment':re.compile(rb'''(?i)(?:api[_-]?key|access[_-]?token|client[_-]?secret)\s*["']?\s*[:=]\s*["']([A-Za-z0-9_./+=-]{24,})["']''')}
objects={}
for line in git('rev-list','--objects','HEAD').decode().splitlines():
 oid,_,p=line.partition(' ')
 if p:objects.setdefault(oid,p)
findings=[];scanned=0;skipped=0
for oid,p in objects.items():
 if git('cat-file','-t',oid).strip()!=b'blob':continue
 size=int(git('cat-file','-s',oid))
 if size>2_000_000:skipped+=1;continue
 b=git('cat-file','blob',oid)
 if b'\0' in b:skipped+=1;continue
 scanned+=1
 for name,pattern in patterns.items():
  count=len(pattern.findall(b))
  if count:findings.append({'object':oid,'path_from_rev_list':p,'pattern':name,'candidate_count':count})
tracked=git('ls-files').decode().splitlines();current=[]
for p in tracked:
 path=r/p
 if not path.is_file() or path.stat().st_size>2_000_000:continue
 b=path.read_bytes()
 if b'\0' in b:continue
 for name,pattern in patterns.items():
  count=len(pattern.findall(b))
  if count:current.append({'path':p,'pattern':name,'candidate_count':count})
report={'source_revision':git('rev-parse','HEAD').decode().strip(),'scope':'HEAD에서 도달 가능한 Git blob의 텍스트 후보. 2MB 초과·NUL 포함 바이너리 제외. 삭제된 브랜치·원격 첨부·이미지 OCR·PDF·플랫폼 설정 제외.', 'text_blobs_scanned':scanned,'skipped_binary_or_large_blobs':skipped,'patterns':list(patterns),'historical_candidate_locations':findings,'current_candidate_locations':current,'tracked_env_files':[p for p in tracked if Path(p).name.startswith('.env') and not p.endswith('.example')], 'interpretation':'후보는 실제 키라는 확정이 아님. 값·부분 값·해시는 출력하지 않음. 키 활성·폐기·재발급을 판정할 수 없음. 미탐 가능.'}
d=r/'docs/verification/final-operations-20261103';d.mkdir(parents=True,exist_ok=True);(d/('secret-scan-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False))
