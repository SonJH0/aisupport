# 3719c28 배포 후 최종 화면 재검증

작성일: 2026-10-29. 사용자 제공 Render 화면의 source 3719c28·Deploy succeeded/Live와 12:54:28 서비스 Live 로그를 확인한 뒤 공개 서비스에서 합성 질문을 시험했다. 저장소 전체 SHA: 3719c28c3ed796bee312428569ccd80a53b4bbd4. 비공개 사전평가 내용은 받거나 기록하지 않았다.

## 새 대화 화면 시험 3회

각 회차를 독립 탭에서 시작했다. AI 고지·외부 전송 안내를 확인하고 동의하지 않은 채 전송을 시도한 뒤, 동의하고 같은 질문을 전송했다.

| 회차 | 질문·원문 | 미동의 시 | 동의 후 실제 결과 | 핵심 기대 결과 |
|---|---|---|---|---|
| 1 | [FastAPI 요청 본문·입력 검증](postdeploy-3719c28/rag-01-ui.json) | 필수 체크 안내, consent=false·valueMissing=true·답변 영역 비어 있음 | backend-1·2와 공식 출처, Pydantic·오류 처리·실습 순서·search_documents 표시 | 충족 |
| 2 | [HTML 폼·접근성](postdeploy-3719c28/rag-02-ui.json) | 같은 화면 차단 확인 | frontend-1·2와 MDN 링크, 폼·접근성 학습 방향·search_documents 표시 | 충족 |
| 3 | [pandas 읽기·결합·요약 통계](postdeploy-3719c28/rag-03-ui.json) | 같은 화면 차단 확인 | data-1·2와 pandas 공식 링크, read_csv·merge·groupby 실습·search_documents 표시 | 충족 |

미동의 화면 차단·AI 고지와 [DOM 관찰](postdeploy-3719c28/consent-before.json), 동의 후 정상 응답은 3회 모두 확인했다. 이번 학습 상담의 핵심 기대 결과는 3/3이다. 기록의 observed_at은 관찰 저장 시각이며 서비스 내부 실행 시각·성능 지표가 아니다. JSON은 화면에서 읽은 텍스트와 링크로, API raw response나 내부 trace를 확보한 기록은 아니다.

서버 직접 요청도 별도로 3회 수행했다. 모두 HTTP 403과 ‘AI 처리를 위한 외부 전송 동의가 필요합니다.’ 본문을 확인했다. [1회](postdeploy-3719c28/consent-server-1.json)·[2회](postdeploy-3719c28/consent-server-2.json)·[3회](postdeploy-3719c28/consent-server-3.json). 화면과 API는 별도 방법이며 같은 네트워크 연결을 추적했다고 주장하지 않는다.

## 기존 증거와의 관계

- [보완 전 추가 시험](final-closure-check.md)의 MDN·pandas 계획 오류는 그대로 보존한다. 이번에는 두 질문 모두 정상 학습 응답을 확인했다. 화면 결과만으로 document_fallback 분기의 실제 실행 여부까지 단정하지 않는다.
- 공고 검색 3종은 앞선 Java·React API와 후속 Python 화면 기록이다. 비교 3건·이미지 API/UI 각 3회도 [최신 텍스트 기록](latest-text-revalidation.md)과 [이미지 기록](../image-validation/image-validation.md)의 버전·방법을 유지한다. 이번 3719c28에서 모든 기능을 새로 3회 수행한 것으로 쓰지 않는다.
- 자동 검사 120개는 [원본](learning-plan-tests.xml)에 있으며 실환경 횟수나 사용자 수와 별개다.
- FastAPI 답변 본문 URL 하나는 닫는 괄호가 링크에 포함됐으나 참고 자료의 공식 URL은 정상 형태다. URL 문장부호 처리·Markdown 표시·답변 길이는 표시 품질 개선점으로 남긴다. 모든 링크 도착 페이지의 최신 내용을 검증한 시험은 아니다.
- 이전 502의 원인·영구 해결은 미확정이다. 이번 3개 화면에서는 계획 오류·502 안내가 나타나지 않았다.

## 최종 상태

이전에 미완료였던 학습 상담 3회와 AI 고지·미동의 차단·동의 후 정상 처리의 화면 3회를 확인해 증거를 추가했다. 기획서·피드백 문서의 오래된 문구는 직전 패치에서 정정됐다. 필수 제출 파일은 저장소에 있으며 플랫폼 URL 저장은 사용자 확인이다. 최종 통과는 평가자의 명세·코드·실행 판단이며, 결과 안내까지 서비스와 AI·검색 API를 유지해야 한다.
