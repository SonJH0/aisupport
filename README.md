# AI 취업 비서

개발 직무 구직·이직 준비자를 위한 AI 상담·공고 후보 검색·경험 비교 서비스입니다. AI 의견은 참고용이며 실제 채용 상태·역량·합격을 보장하지 않습니다.

## 서비스와 문서

- **배포:** https://ai-job-assistant-xewt.onrender.com
- **저장소:** https://github.com/SonJH0/aisupport
- 로그인 없이 사용합니다. 기능 선택 → 질문 또는 공고·경험 입력 → 외부 전송 동의 → 전송 순서입니다. 이미지는 취업 상담에서 첨부합니다. 비교에는 공고 본문 또는 이미지를 제공하세요. 링크만으로 원문을 읽지는 않습니다.
- **[제출 문서 안내](docs/README.md)** · [Must 확인 방법](docs/요구사항-정의서.md) · [진행·남은 작업](docs/진행-및-제출현황.md)

## 기능과 결과

| 기능 | 동작·검증 |
|---|---|
| AI 상담·RAG | 질문별 문서 본문 검색·출처 기반 답변. [배포 검증](docs/verification/deployment-validation.md) |
| 공고 후보 검색 | 인터넷 검색·목록/강의 필터·요약 조건 확인 구분. [필터 기록](docs/verification/search-filter-change.md) |
| 적합도 비교 | 입력 근거로 일치·차이·정보 부족 및 보완 안내. [배포 검증](docs/verification/deployment-validation.md) |
| 이미지 분석 | 이미지 판독·미제공·비공고 구분. [API 3회와 화면 3회 별도 기록](docs/image-validation/image-validation.md) |

자동 검사 74개 및 기술 테스트 기록이 있습니다. [팀원 외 취업 준비생 5명의 피드백](docs/사용자-피드백-기록.md)을 수집·전사했습니다. 의견 원문 이미지와 기능 유지 판단을 기록했습니다. [발표 PDF·PowerPoint·13장 이미지](docs/presentation/README.md)를 제출 자료로 제공합니다. 실제 수집 질문·구체적인 타깃 근거·공개 캡처의 식별정보는 최종 점검 항목입니다. 수정 전 실패·부분 성공은 보존합니다. 기술 테스트를 실제 사용자 피드백으로 세지 않습니다.

## 팀원과 역할

| 이름 / 계정 | 담당 범위 | 대표 기록 |
|---|---|---|
| 손재형 / SonJH0 | AI/Data·RAG·Agent·검색 필터·검증 정리 | [7408e14](https://github.com/SonJH0/aisupport/commit/7408e14), [e101485](https://github.com/SonJH0/aisupport/commit/e101485) |
| 손재윤 / sonjeyun | 백엔드 | [f228f33](https://github.com/SonJH0/aisupport/commit/f228f33) |
| 황준식 / kwork0828 | 프론트엔드 | [aec3c4a](https://github.com/SonJH0/aisupport/commit/aec3c4a) |

세 명의 [본인 기여 요약과 대표 커밋](docs/팀원별-기여.md)을 작성했습니다. 역할과 구현·검증 내용을 확인할 수 있습니다.

## 기술 선택·구현

Python 3.12·FastAPI·Pydantic으로 AI 코드·API·입력 검증을 통합했습니다. HTML/CSS/JavaScript 화면은 Render의 같은 서버에서 제공합니다. 코디세이 OpenAI 호환 API가 도구를 선택하고, Claude 호환 API가 이미지를 직접 읽습니다. Brave Search로 공고 후보를 찾으며, 소규모 문서는 로컬 JSON·TF-IDF로 검색합니다. GitHub·Actions로 버전과 검사를 관리합니다.

- Agent: `ai/agent.py`의 LLM 도구 선택·실행 결과 전달. 네이티브 반복 및 JSON 계획 경로 지원.
- RAG: `ai/retrieval.py`의 질문별 본문 검색 결과를 LLM에 전달. 의미 임베딩은 아님.
- 멀티모달: `ai/vision.py`에서 이미지 직접 입력. 선명한 영어 PNG 3종 실제 확인.
- 장기 메모리·일정 자동화는 구현 기술로 주장하지 않습니다. 상세 선정 이유·아키텍처는 [기획서](docs/프로젝트-기획서.md)와 [명세서](docs/요구사항-정의서.md)에 있습니다.

## 설치·실행

```powershell
git clone https://github.com/SonJH0/aisupport.git
cd aisupport
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

`.env`에 실제 키를 설정합니다: `OPENAI_API_KEY`, `OPENAI_BASE_URL=https://copa.codyssey.kr/v1`, `OPENAI_MODEL=gpt-5-mini`, `AGENT_TOOL_MODE=auto`. 공고 검색에는 `BRAVE_SEARCH_API_KEY`, 이미지에는 `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL=claude-haiku-4`가 필요합니다. 실제 키는 커밋하지 않습니다.

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

http://127.0.0.1:8000 에 접속합니다. 화면은 `frontend/`에서 제공하며 별도 5500 서버나 Vercel 배포는 필요하지 않습니다. Git 작업은 실제 저장소 폴더에서 진행합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Render: 빌드 `pip install -r requirements.txt`, 시작 `python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT`, 상태 검사 `/health`. 키는 Render 환경변수에 설정하고 결과 안내까지 서비스를 유지하세요.

## 최종 확인

[최종 점검표](docs/최종-점검표.md)에서 Must별 시험 결과와 제출 확인 항목을 관리합니다. 기존 기술 검증은 보존하며, 미실행 항목을 성공으로 표시하지 않습니다.

## 제한·개인정보

화면에서 AI 생성 정보와 외부 전송을 알리고 동의를 받으며 서버도 미동의를 차단합니다. 입력·이미지·최근 대화는 코디세이 AI, 공고 검색어는 Brave로 전송됩니다. 대화 DB는 없고 새 대화·새로고침 시 이력이 지워집니다. 외부 제공자·배포 로그의 삭제까지 보장하지 않습니다. 개인정보를 가리고 사용하며 피드백은 가명으로 보관합니다.

공고 원문·모집 상태는 직접 확인해야 합니다. 필터의 조건·사이트 인식, 이미지 출처 관련성, Markdown 원문 표시에는 한계가 있습니다. 과거 노출 키의 폐기 상태와 공개 피드백 이미지 5개의 식별정보 없음은 2026-10-29 담당자가 확인했습니다. [보안 확인 범위](docs/verification/security-confirmation.md)를 참고하세요. 저장소 전체 이력 점검과 기존 직무 추천 요구·현재 공고 검색의 범위 차이는 별도 확인 항목입니다.

검증 원본은 `docs/verification/`, 이미지 자료는 `docs/image-validation/`, 이전 초안·사용하지 않는 코드는 `docs/archive/`에 보존합니다. [문서 안내](docs/README.md)에서 필요한 자료를 찾을 수 있습니다.



