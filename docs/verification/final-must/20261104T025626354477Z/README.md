# 최신 배포 Must 최종 점검 결과

실행: 2026-11-04 11:56~12:08 KST. 모든 24개 요청 직전 `/health`에서 **05373a22fc3319ecd042e1f264787fd352abd3b6**을 관찰했다. 실제 AI 요청 18건 모두 HTTP 200, 미동의·동의 누락 요청 6건 모두 HTTP 403. 자동 재시도·실패 삭제 없이 원본을 보존했다. 새 브라우저 시험은 아니며 [기존 화면 5장](../../final-ui-20261104/README.md)과 구분한다.

## 기능별 내용 검토

| 범위 | 입력·회차 | 내용 검토 결과 |
|---|---|---|
| 원래 평가: 스펙 분석 | 같은 Python API·SQL 조회 경험 3회 | 핵심 충족 2/3, 부분 충족 1/3. 1회차 pandas ORM 예시 오류도 별도 주의 |
| 원래 평가: 직무 추천 | 같은 Python API·SQL 경험 3회 | 잠정 후보 2개·이유·확인 질문 3/3 |
| FR-01 상담·RAG | 같은 FastAPI 요청 본문 학습 질문 3회 | 검색 본문·backend-1 출처·학습 순서 연결 3/3. 상세 API 버전 정확성과 구분 |
| FR-02 공고 후보 | Python/FastAPI·Java/Spring Boot·React/TypeScript 각 1회, 합계 3회 | 개별 후보·조건 구분·출처·모집 미확인 표시 3/3. 같은 검색 입력 반복 안정성 시험은 아님 |
| FR-03 비교 / 원래 평가 Agent 비교 경로 | Python 경험 있음·Java 못함·Kotlin 미언급 대 공고 3회 | 일치·차이·정보 부족, 근거·확인 질문·행동 3/3 |
| FR-04 이미지 | 기존 가상 공고 2종·영수증 1종, 각 1회 | 엄격 집계 핵심 충족 2/3, 부분 충족 1/3. 판독은 3건 핵심 정보 확인 |
| FR-05 고지·동의 | consent=false 3회, 누락 3회, HTML 3회, 위 동의 후 상담 3회와 연결 | 서버 차단 각 3/3, 고지·필수 동의 HTML 3/3, 동의 후 상담 3/3. 신규 브라우저 클릭 시험 아님 |

G4의 ‘기능마다 3회 중 2회’ 기준과 대조할 수 있는 핵심 동작 근거다. 서로 다른 이미지·검색 입력은 같은 입력 3회 반복 시험으로 표시하지 않는다. 원래 평가 기능인 직무 추천과 공고 검색도 구분한다. 공식 G4 충족 판단은 평가자의 명세·실제 실행 확인에 따른다.

## 남은 내용 품질 한계

- spec-1: pandas를 ORM의 예로 제시한 부정확한 용어 사용. 스펙 사실 추출과 구분해 기록한다.
- spec-2: 조회 경험에서 CRUD 수준을 추론. 엄격한 내용 집계에서 부분 충족으로 처리했다.
- image-1: AWS가 미기재임을 표시하고 질문했으나, 경험이 없거나 정리하지 않은 상태로 보인다는 추측을 덧붙였다. 이 회차를 완전 충족으로 세지 않았다.
- chat-1/3의 validator/root_validator 등 상세 실습 API는 자료 밖 제안이며 최신 버전별 사용법을 독립 검증하지 않았다. 인용한 검색 요약의 범위와 분리한다.
- 이미지 sources는 모두 빈 배열이고 image_analysis=ok, initial_retrieval=skipped_image_only다. 무관한 학습 출처 혼입은 관찰되지 않았다.
- 검색은 Python 후보 4개 모두 추가 확인, Java 조건 일치 2개·추가 확인 3개, React 조건 일치 2개를 표시했다. 제외 항목 전문·검색 요약 원문 전체·현재 모집 상태는 원본 응답에 없거나 독립 검증하지 않아 정확성을 확대하지 않는다.
- 학습 상담 3회는 문서 검색 fallback 경로다. 도구명만 보고 LLM이 자율 선택했다고 주장하지 않는다. compare/search 실행도 해당 요청 경로 근거이며 모든 Agent 분기의 선택 정확성이나 반복 계획을 증명하지 않는다. Agent 구조·이전 선택 기록은 기존 코드·버전별 증거와 함께 읽는다.

## 원본과 재현

[실행 목록](run.json) · [회차별 수동 검토](review.json). 아래 파일의 request에는 이미지 base64 대신 기존 PNG 경로·SHA-256·크기를 기록했다. 원본의 review='미판정'은 보존하고 수동 판단은 별도 review.json에 적었다.

- [agent-1.json](agent-1.json): 핵심 충족 — compare_requirements 실행, Python 일치·Java 차이·Kotlin 정보 부족, 근거·질문·행동 일관. 세 응답 내용 동일. 모든 Agent 분기 검증으로 확대하지 않음.
- [agent-2.json](agent-2.json): 핵심 충족 — compare_requirements 실행, Python 일치·Java 차이·Kotlin 정보 부족, 근거·질문·행동 일관. 세 응답 내용 동일. 모든 Agent 분기 검증으로 확대하지 않음.
- [agent-3.json](agent-3.json): 핵심 충족 — compare_requirements 실행, Python 일치·Java 차이·Kotlin 정보 부족, 근거·질문·행동 일관. 세 응답 내용 동일. 모든 Agent 분기 검증으로 확대하지 않음.
- [chat-1.json](chat-1.json): 핵심 충족·세부 한계 — backend-1 검색·출처·학습 순서 연결. 세 회차 모두 empty_plan_document_fallback 경로. 상세 API 예시는 버전별 정확성 검증 대상 아님.
- [chat-2.json](chat-2.json): 핵심 충족·세부 한계 — backend-1 검색·출처·학습 순서 연결. 세 회차 모두 empty_plan_document_fallback 경로. 상세 API 예시는 버전별 정확성 검증 대상 아님.
- [chat-3.json](chat-3.json): 핵심 충족·세부 한계 — backend-1 검색·출처·학습 순서 연결. 세 회차 모두 empty_plan_document_fallback 경로. 상세 API 예시는 버전별 정확성 검증 대상 아님.
- [consent-1.json](consent-1.json): 충족 — HTTP 403 및 외부 전송 동의 필요 안내. consent 회차의 HTML 고지·required 존재도 확인. 브라우저 실제 조작 시험 아님.
- [consent-2.json](consent-2.json): 충족 — HTTP 403 및 외부 전송 동의 필요 안내. consent 회차의 HTML 고지·required 존재도 확인. 브라우저 실제 조작 시험 아님.
- [consent-3.json](consent-3.json): 충족 — HTTP 403 및 외부 전송 동의 필요 안내. consent 회차의 HTML 고지·required 존재도 확인. 브라우저 실제 조작 시험 아님.
- [image-1.json](image-1.json): 부분 충족 — 회사·직무·지역·Python 최소 2년 대 입력 1년·SQL·AWS 우대·마감 미제공은 정확. 그러나 AWS에 경험이 없거나 아직 정리하지 않은 상태로 보인다는 추측이 있어 엄격 집계에서 제외.
- [image-2.json](image-2.json): 핵심 충족 — DEMO STUDIO·Frontend Developer·React/TypeScript·가상 표시, 경력/급여/마감 미제공 구분.
- [image-3.json](image-3.json): 핵심 충족 — DEMO CAFE 영수증·수량/금액/합계 판독, 비공고 판단, 채용 요건 창작 없음.
- [missing-consent-1.json](missing-consent-1.json): 충족 — HTTP 403 및 외부 전송 동의 필요 안내. consent 회차의 HTML 고지·required 존재도 확인. 브라우저 실제 조작 시험 아님.
- [missing-consent-2.json](missing-consent-2.json): 충족 — HTTP 403 및 외부 전송 동의 필요 안내. consent 회차의 HTML 고지·required 존재도 확인. 브라우저 실제 조작 시험 아님.
- [missing-consent-3.json](missing-consent-3.json): 충족 — HTTP 403 및 외부 전송 동의 필요 안내. consent 회차의 HTML 고지·required 존재도 확인. 브라우저 실제 조작 시험 아님.
- [role-1.json](role-1.json): 핵심 충족 — 직무 후보 2개·입력 경험에 근거한 이유·추가 확인 질문. 공고 검색 없음. 적합성 확정이 아닌 잠정 제안.
- [role-2.json](role-2.json): 핵심 충족 — 직무 후보 2개·입력 경험에 근거한 이유·추가 확인 질문. 공고 검색 없음. 적합성 확정이 아닌 잠정 제안.
- [role-3.json](role-3.json): 핵심 충족 — 직무 후보 2개·입력 경험에 근거한 이유·추가 확인 질문. 공고 검색 없음. 적합성 확정이 아닌 잠정 제안.
- [search-1.json](search-1.json): 핵심 충족 — search_live_jobs 실행·개별 후보·링크·요약 조건 구분·현재 모집 미확인 표시. 목록 혼입 관찰 없음. 검색 원문 전체/제외 후보/현 모집 상태를 독립 검증한 것은 아님.
- [search-2.json](search-2.json): 핵심 충족 — search_live_jobs 실행·개별 후보·링크·요약 조건 구분·현재 모집 미확인 표시. 목록 혼입 관찰 없음. 검색 원문 전체/제외 후보/현 모집 상태를 독립 검증한 것은 아님.
- [search-3.json](search-3.json): 핵심 충족 — search_live_jobs 실행·개별 후보·링크·요약 조건 구분·현재 모집 미확인 표시. 목록 혼입 관찰 없음. 검색 원문 전체/제외 후보/현 모집 상태를 독립 검증한 것은 아님.
- [spec-1.json](spec-1.json): 핵심 충족·세부 주의 — Python API·SQL 경험과 추가 질문 구분. pandas를 ORM 예시에 포함한 기술 용어 오류는 남음.
- [spec-2.json](spec-2.json): 부분 충족 — SQL 조회 경험에서 기본 CRUD 수준으로 해석을 넓힌 문장이 있어 엄격 집계에서 제외.
- [spec-3.json](spec-3.json): 핵심 충족 — 입력 경험·미기재 프레임워크/운영/성능을 구분. 숙련도·규모를 확정하지 않음.

재현: 저장소 루트에서 `py -3 tools/verify-final-must.py`. `--dry-run`은 입력만 확인한다. 실제 실행은 당시 로컬 HEAD와 매 요청 직전 배포 revision이 같아야 진행한다. 도구·문서를 반영한 새 커밋은 이 실행의 SHA와 달라지므로 원본의 실행 버전을 바꾸지 않는다. 이번 작업에서 backend/·frontend/·ai/는 수정하지 않았다.

이 실행은 입력을 고정한 API 확인이다. 지속 가용성, 전 입력 정확성, 새 UI·외부 제공자 전체 키 감사 또는 공식 PASS를 보장하지 않는다. 과거 실패 기록도 그대로 보존한다.
