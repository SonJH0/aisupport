"""사용자가 입력한 경험과 공고 문장을 짝짓는다. 합격·역량 점수는 만들지 않는다."""
import re


def _experience_status(requirement, lines):
    """기간·숙련도 조건이 없는 단순 기술 경험 요건만 보수적으로 구분한다."""
    match = re.fullmatch(r"(Python|Java|Kotlin|SQL|React|TypeScript|FastAPI)\s*(?:API\s*)?(?:개발|사용)?\s*경험[.!]?", requirement, re.I)
    if not match:
        return None
    skill = match.group(1)
    pattern = r"(?<![a-z0-9])" + re.escape(skill) + r"(?![a-z0-9])"
    relevant = [line for line in lines if re.search(pattern, line, re.I)]
    if not relevant:
        return "정보 부족"
    signals = set()
    for line in relevant:
        # 한 문장에 여러 기술이나 복합 부정이 있으면 단정하지 않는다.
        if len(re.findall(r"(?<![a-z0-9])(?:Python|Java|Kotlin|SQL|React|TypeScript|FastAPI)(?![a-z0-9])", line, re.I)) != 1:
            return None
        tail = re.split(pattern, line, maxsplit=1, flags=re.I)[1]
        if re.search(r"없지|않지|못.*(?:아니|없)|모르.*아니|없.*아니", tail):
            return None
        if re.search(r"^\s*(?:은|는|을|를)?\s*(?:경험이?\s*|(?:사용|개발)(?:해\s*본\s*적이?|한\s*경험이?|할\s*줄|하지|한\s*적이?)?\s*)?(?:없|못|모르|모릅|않)", tail):
            signals.add("차이")
        elif re.search(r"사용했|사용한|사용해\s*봤|만들|개발했|개발한|구현했|구현한|경험이?\s*있", tail):
            signals.add("일치")
        else:
            return None
    return signals.pop() if len(signals) == 1 else None


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
        row = {"requirement": requirement, "user_evidence": lines[:3],
               "status": "관련 표현 있음; 의미 확인 필요" if lines else "정보 부족"}
        experience_status = _experience_status(requirement, lines)
        if experience_status is not None:
            row.update(status=experience_status, experience_status=experience_status,
                       proficiency_status="미확인; 경험 유무와 별도 확인")
        rows.append(row)
    return {"status": "ok", "requirements": rows,
            "limitation": "어휘 근거 비교다. 부정문, 숙련도와 경력 기간을 확인해야 한다. 언급 없음은 미보유가 아니다."}

