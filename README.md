# AI 취업 비서

개발 직무를 준비하는 구직·이직 준비자가 학습 자료를 찾고, 채용공고 후보를 검색하고, 자신의 경험을 공고 요건과 비교하도록 돕는 AI 서비스입니다. AI 의견은 참고용이며 실제 채용 상태·역량·합격 가능성을 보장하지 않습니다.

## 배포 주소와 평가자 사용 방법

- 서비스: https://ai-job-assistant-xewt.onrender.com
- 저장소: https://github.com/SonJH0/aisupport
- 로그인 없이 사용합니다. 별도 평가 계정은 필요하지 않습니다.
- `취업 상담`, `공고 추천`, `적합도 비교` 중 선택해 입력한 다음 외부 AI 전송 동의를 체크하고 전송합니다. 이미지 분석은 기본 취업 상담에서 이미지 파일을 첨부하고 질문합니다.
- 공고 링크만 입력하면 원문 내용을 읽지 않습니다. 비교에는 공고 본문 또는 이미지를 제공해야 합니다.
- 평가용 이미지·질문·기대 결과는 [이미지 검증 기록](docs/image-validation/image-validation.md)에 있습니다. 실제 개인정보가 없는 자료를 사용하세요.
- 첫 접속이나 응답이 지연되면 잠시 기다린 뒤 다시 시도하세요. 접속 확인은 `/health`에서 가능합니다. 결과 안내를 받을 때까지 서비스와 API 사용 가능 상태를 유지해야 합니다.

## 기능과 현재 결과

| 기능 | 동작 | 확인 기록 |
|---|---|---|
| AI 상담·문서 검색 | 질문별 관련 문서 본문을 검색해 AI 답변과 출처 제공 | [배포 기능 검증](docs/deployment-validation.md) |
| 공고 후보 검색 | 인터넷 검색 후 강의·목록·명시적 마감·신입 경력 충돌 결과 제외, 요약 조건 일치/추가 확인 필요 구분 | [검색 필터](docs/search-filter-change.md), [인크루트 보완](docs/incruit-filter-fix.md), [진행 기록](docs/진행-및-제출현황.md) |
| 적합도 비교 | 입력 경험과 공고의 항목별 근거, 일치·차이·정보 부족과 확인 질문 제공 | [배포 기능 검증](docs/deployment-validation.md) |
| 이미지 분석 | 이미지 자체를 모델에 전송해 판독하고 미제공 정보 구분 | [이미지 API 3회 및 화면 확인](docs/image-validation/image-validation.md) |

기술 테스트는 실제 사용자 5명의 피드백이 아닙니다. 실제 사용자 피드백과 발표 PDF는 아직 완료되지 않았습니다. 수정 전 실패·부분 성공 기록은 보존하고, 이후 재검증 관찰은 별도로 기록합니다. 이번 문서 정리만으로 평가 기준 통과를 확정하지 않습니다.

## 팀원과 역할

| 이름 / GitHub | 담당 범위 | 코드에서 확인한 대표 기록 | 본인이 쓴 기여 요약 |
|---|---|---|---|
| 손재형 / SonJH0 | AI/Data, RAG·Agent·검색 필터 및 검증 정리 | [7408e14](https://github.com/SonJH0/aisupport/commit/7408e14), [2789a88](https://github.com/SonJH0/aisupport/commit/2789a88), [e101485](https://github.com/SonJH0/aisupport/commit/e101485) | [본인 작성 필요](docs/팀원별-기여.md) |
| 손재윤 / sonjeyun | 백엔드 | [f228f33](https://github.com/SonJH0/aisupport/commit/f228f33) | [본인 작성 필요](docs/팀원별-기여.md) |
| 황준식 / kwork0828 | 프론트엔드 | [aec3c4a](https://github.com/SonJH0/aisupport/commit/aec3c4a) | [본인 작성 필요](docs/팀원별-기여.md) |

역할은 기존 문서의 표기를 유지했습니다. 커밋에 다른 디렉터리의 파일이 함께 들어갈 수 있으므로 파일 경로만으로 개인의 모든 작업을 단정하지 않습니다. AI 보조로 코드·문서와 기술 테스트를 작성했고, 각 팀원의 실제 검토·수정·테스트 범위는 본인이 작성해야 합니다.

## 기술 스택과 선택 이유

| 구성 | 사용 기술 | 선택 이유 |
|---|---|---|
| 서버 | Python 3.12, FastAPI, Uvicorn, Pydantic | AI 코드와 입력 검증·API를 같은 언어로 구성하고 화면도 함께 제공 |
| 텍스트 AI | 코디세이 OpenAI 호환 API, gpt-5-mini 설정 | 자연어 상담과 모델의 도구 선택을 서비스에 연결 |
| 이미지 AI | 코디세이 Claude 호환 API, claude-haiku-4 설정 | 이미지 파일을 직접 모델 입력으로 전달 |
| 문서 검색 | 로컬 JSON, 단어·문자 2-gram TF-IDF/코사인 유사도 | 작은 자료집에서 외부 DB 없이 본문 검색·출처 추적 구현. 의미 검색과 큰 자료집에는 한계 |
| 웹 검색 | Brave Search API | 인터넷 공고 후보·검색 요약 확보. 원문·현재 모집 상태 검증을 대신하지 않음 |
| 화면 | HTML, CSS, JavaScript | 별도 프론트 빌드 과정 없이 입력·첨부·답변 화면 구성 |
| 배포·관리 | Render, GitHub, GitHub Actions/pytest | 화면·API를 한 서비스로 배포하고 소스·문서·검사 결과 버전 관리 |

## 시스템과 AI 활용

브라우저에서 FastAPI `/api/chat`으로 요청합니다. 텍스트는 매번 문서 본문 검색 → LLM이 4개 도구 중 선택 → 허용 인자 검사·실행 → 결과 전달·최종 답변 순서입니다. 이미지 첨부는 별도의 이미지 모델 경로로 전달됩니다. 상세 다이어그램과 기술별 코드는 [요구사항 정의서](docs/요구사항-정의서.md)에 있습니다.

- **Agent**: `ai/agent.py`의 `TOOLS`, `respond`, `_json_agent`, `run_tool`. 네이티브 tool_calls와 미지원 시 JSON 계획을 실제 실행합니다. JSON 경로는 단일 계획 후 실행이며 다회 재계획이라고 표현하지 않습니다.
- **RAG**: `ai/retrieval.py`의 `search_documents`, `rank_documents`. `data/knowledge.json`과 저장 공고 후보의 문단을 질문마다 검색해 LLM 입력에 넣습니다. 고정 텍스트를 항상 붙이는 구조와 다르며 의미 임베딩은 사용하지 않습니다.
- **멀티모달**: `ai/vision.py`의 `analyze_image`. PNG/JPEG/WebP를 직접 입력합니다. 실제 확인 범위는 선명한 영어 PNG 3개이며 모든 이미지의 정확도를 보장하지 않습니다.
- 최근 대화는 화면 메모리에만 유지됩니다. 세션 종료 후 저장되는 Long-term Memory나 일정·이벤트 자동화는 구현하지 않았으며 기술 요소로 주장하지 않습니다.

## 로컬 실행

Python 3.12를 준비하고 저장소를 복제한 뒤 프로젝트 최상위에서 실행합니다.

```powershell
git clone https://github.com/SonJH0/aisupport.git
cd aisupport
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

`.env`에 `OPENAI_API_KEY`, `OPENAI_BASE_URL=https://copa.codyssey.kr/v1`, `OPENAI_MODEL=gpt-5-mini`, `AGENT_TOOL_MODE=auto`를 설정합니다. 공고 검색에는 `BRAVE_SEARCH_API_KEY`, 이미지에는 `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL=claude-haiku-4`가 필요합니다. 실제 키는 저장소에 올리지 않습니다. `CODYSSEY_API_KEY`는 OpenAI 키의 대체 변수명으로 지원합니다.

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

http://127.0.0.1:8000 에 접속합니다. 화면도 같은 서버가 제공하므로 별도 5500 서버는 필요하지 않습니다. 기존 작업 폴더 이름은 자유이며, Git 작업은 실제 저장소인 `ai-job-assistant-git`에서 진행합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Render의 시작 명령은 `python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT`, 빌드 명령은 `pip install -r requirements.txt`, Health Check는 `/health`입니다. 키는 Render 환경변수에 설정합니다.

## 개인정보·제한

화면에서 AI 생성 정보임을 안내하고 외부 전송 동의를 받습니다. 미동의 요청은 서버에서도 차단합니다. 입력·이미지·최근 대화는 코디세이 AI에, 공고 검색어는 Brave Search에 전송됩니다. 앱은 대화 DB를 만들지 않으며 새 대화·새로고침 시 화면 이력이 지워집니다. 외부 제공자나 배포 서비스 로그의 보관·삭제까지 보장하지 않습니다. 사용자 피드백은 T1 등 가명으로 기록하고 이름·연락처는 저장소에 올리지 않습니다.

공고 상태·기술·경력 요건은 원문에서 확인해야 합니다. 필터는 검색 요약에 의존하며 모든 페이지·조건을 판정하지 않습니다. 이미지 답변의 관련 없는 출처와 Markdown 문법이 그대로 보이는 화면 가독성 문제도 남아 있습니다. 과거 노출 키의 폐기·재발급은 완료 증빙이 확인되지 않아 제출 전 별도 확인이 필요합니다.

## 문서와 남은 작업

- [기획서](docs/프로젝트-기획서.md)
- [기능·비기능 요구사항, 아키텍처, 구현 현황](docs/요구사항-정의서.md)
- [진행·재검증·제출 현황](docs/진행-및-제출현황.md)
- [팀원별 기여 작성란](docs/팀원별-기여.md): 각 팀원 본인이 작성할 것
- [실사용자 피드백 수집 안내](docs/사용자-피드백-수집안내.md): 현재 실제 응답 0명 확인
- 발표 PDF: 미제출. 피드백·개선 후 `docs/`에 PDF를 추가하고 링크할 것

과거 `docs/기획-및-요구사항.md`, `docs/AI-data-작업.md` 등은 당시 초안·설명으로 보존합니다. 현재 상태의 기준 문서는 위 기획서·요구사항 정의서이며, 서로 다른 버전의 검증을 동일 버전 3회 성공으로 합치지 않습니다. 과거 평가에서 언급된 '직무 추천'과 현재 '공고 후보 검색'의 요구 범위가 같다는 합의는 확인되지 않았습니다. 원래 제출 명세가 직무 리스트를 요구한다면 해당 기능을 별도로 충족·검증해야 합니다.
