# AI 취업 비서

구직·이직 준비자를 위한 개발용 서비스입니다. 직무 학습 자료를 검색하여 상담하고, 실제 도구 실행을 통해 공고 후보 검색 및 입력 공고와 경험 비교를 지원합니다. AI 의견은 참고용이며 합격이나 채용 상태를 보장하지 않습니다.

## Windows / VS Code 실행

프로젝트 최상위 `ai-job-assistant` 폴더를 VS Code로 엽니다. Python 3.12를 기준으로 검사했습니다. 기존 `.env`와 `.git`, 가상환경은 삭제하거나 업로드하지 마세요.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

기존 `.env`가 있다면 그대로 사용합니다. 없을 때만 `.env.example`을 `.env`로 복사하고 키를 설정합니다.

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

- `OPENAI_API_KEY`: 코디세이 OpenAI 호환 키. `CODYSSEY_API_KEY`도 대체 이름으로 지원합니다.
- `OPENAI_MODEL`: 기본 `gpt-5-mini`.
- `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`: 기존 이미지 분석 기능의 코디세이 Anthropic 호환 설정.
- `BRAVE_SEARCH_API_KEY`: 선택 기능인 실시간 웹 검색용. 없으면 검색을 했다고 주장하지 않고 설정 필요를 안내합니다.
- `AGENT_TOOL_MODE=auto`: 네이티브 도구 호출을 우선 사용하고, 미지원 또는 도구 미실행 응답에서는 검증된 JSON 계획을 실제 실행합니다. `native`, `json`으로 명시할 수도 있습니다.

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

브라우저에서 http://127.0.0.1:8000 을 엽니다. 같은 서버가 프론트엔드와 API를 함께 제공하므로 별도 5500 서버는 필요하지 않습니다. 상태는 `/health`, 개발용 API 문서는 `/docs`에서 확인합니다. 이 주소는 외부 배포 URL이 아닙니다.

폴더 위치와 설치를 한 번에 처리하려면 프로젝트 폴더에서 `powershell -ExecutionPolicy Bypass -File .\start-backend.ps1`을 사용할 수 있습니다. 해당 시작 스크립트는 Python 3.12가 없는 새 환경에서는 설치 확인을 요청합니다.

## 핵심 구현

- `ai/retrieval.py`: 매 요청마다 `data/knowledge.json`과 저장 공고 후보의 본문을 검색합니다. 단어·문자 2-gram TF-IDF와 코사인 유사도 기반이며 의미 임베딩 검색은 아닙니다. 검색 문단 ID·점수·출처가 반환됩니다. 가상 공고는 일반 RAG 근거에서 제외합니다.
- `ai/agent.py`: LLM이 `search_documents`, `search_live_jobs`, `get_job`, `compare_requirements` 중 호출 도구와 인자를 정합니다. 허용 목록·인자 검증 후 실제 실행하고 결과를 모델에 전달합니다. 요청당 네이티브 반복 4회, 전체 도구 호출 8회로 제한합니다. JSON 계획 경로는 최대 3개 도구를 실행합니다.
- `ai/comparison.py`: 사용자가 실제 입력한 경험·공고 문장을 비교합니다. 어휘 근거만 제시하며 부정문·숙련도·기간은 추가 확인합니다. 정보 미기재를 능력 미보유로 단정하지 않습니다.
- `ai/vision.py`: 기존 Claude 호환 이미지 직접 분석을 유지하고 초기 문서 검색 근거를 전달합니다. 실제 공고 이미지에서 별도 검증이 필요합니다.
- `backend/main.py`: `/api/chat` 계약을 유지하고 서버에서도 동의를 검사합니다. 요청 본문은 `message`, `history`, `image`, `consent`입니다. 응답의 기존 `answer`, `tools`와 함께 `sources`, `trace`, `ai_generated`를 제공합니다.

## 검증

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

새 자동 테스트는 실제 사용자 피드백이 아닙니다. 검사 범위와 실제 API 검사 결과는 `docs/RAG-Agent-보완.md`, `docs/actual-api-check.json`에서 확인합니다. 평가 기준의 각 Must 기능 3회 시도와 실사용자 5명 조건이 완료됐다는 의미가 아닙니다.

## 데이터와 개인정보

공식 학습 문서의 팀 요약은 채용 필수 기준이 아닙니다. 저장 공고 후보의 원문과 현재 모집 상태는 직접 확인해야 하며 최신성 자동 검증은 없습니다. 브라우저의 최근 대화 10개는 후속 질문에 함께 전송되고 새 대화·새로고침 시 지워집니다. 서버는 대화 DB를 만들지 않습니다. 외부 AI·검색 제공자의 데이터 처리 정책은 별도로 확인해야 합니다. 이름·연락처와 민감한 정보는 가리고 사용합니다. 동의하지 않은 요청은 서버가 403으로 차단합니다.

## 역할

원본 문서의 역할 표기를 유지합니다: 손재형 — AI/Data(`ai/`, `data/`), 손재윤 — 백엔드(`backend/`), 황준식 — 프론트엔드(`frontend/`). 실제 분담이 바뀌었다면 팀이 확인하여 수정하세요. 이번 수정본은 AI 보조 작업이며 팀원별 실제 검토·수정·테스트 내용을 본인 기여 기록에 구분해 남기세요.

## 남은 제출 작업

외부 배포, 필수 기능별 실환경 반복 검증, 팀원을 제외한 사용자 5명 이상의 실제 테스트, 익명 응답 원본, 피드백 반영, 최종 명세와 발표 PDF가 필요합니다. RAG·Agent 인정 여부는 평가자의 실제 확인에 따릅니다.
