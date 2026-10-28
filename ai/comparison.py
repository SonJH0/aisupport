"""사용자가 입력한 경험과 공고 문장을 짝짓는다. 합격·역량 점수는 만들지 않는다."""
import re


def compare_requirements(message):
    match = re.search(r"\[지원자의 경험\]\s*(.*?)\s*\[채용공고\]\s*(.+)", message, re.S)
    if not match or not all(part.strip() for part in match.groups()):
        return {"status": "needs_input", "message": "적합도 비교 화면에 실제 경험과 공고 내용을 각각 입력해 주세요."}
    experience, job = match.groups()
    split = lambda text: [s.strip(" -•\t") for s in re.split(r"[\n。]+|(?<=[.!?])\s+", text) if s.strip(" -•\t")]
    rows = []
    for requirement in split(job)[:30]:
        terms = set(re.findall(r"[a-z][a-z0-9+#.]*|[가-힣]{2,}", requirement.casefold()))
        terms -= {"경험", "우대", "필수", "이상", "가능", "대한", "활용", "또는"}
        lines = [line for line in split(experience) if any(term in line.casefold() for term in terms)]
        rows.append({"requirement": requirement, "user_evidence": lines[:3],
                     "status": "관련 표현 있음; 의미 확인 필요" if lines else "정보 부족"})
    return {"status": "ok", "requirements": rows,
            "limitation": "어휘 근거 비교다. 부정문, 숙련도와 경력 기간을 확인해야 한다. 언급 없음은 미보유가 아니다."}
