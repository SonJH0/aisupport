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
        terms -= {"경험", "우대", "필수", "이상", "가능", "대한", "활용", "또는", "개발", "사용"}
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



def render_comparison(result):
    """분류와 후속 행동을 같은 도구 근거에서 생성해 미기재 역량을 창작하지 않는다."""
    if result.get("status") != "ok":
        return result.get("message", "경험과 공고 내용을 각각 제공해 주세요.")
    parts = ["입력한 경험과 공고의 어휘 근거 비교입니다. 실제 역량·합격 가능성 평가가 아닙니다."]
    for row in result["requirements"]:
        status = row["status"]
        parts += ["", f"요건: {row['requirement']}", f"판정: {status}"]
        evidence = row.get("user_evidence", [])
        parts.append("입력 근거: " + (" / ".join(evidence) if evidence else "관련 경험이 입력되지 않았습니다. 미보유를 뜻하지 않습니다."))
        if status == "일치":
            parts += ["확인 질문: 본인의 역할·구현 내용·결과를 설명할 수 있나요?",
                      "보완 행동: 실제 프로젝트 사례와 본인 기여를 정리하세요. 숙련도와 규모는 별도 확인이 필요합니다."]
        elif status == "차이":
            parts += ["확인 질문: 명시한 경험 부족이 현재도 해당하나요? 공고의 필수·우대 구분은 무엇인가요?",
                      "보완 행동: 명시적으로 부족하다고 적은 경험에 한해 학습·실습 계획을 세우고 실제 경험과 계획을 구분하세요."]
        elif status == "정보 부족":
            parts += ["확인 질문: 이 요건에 해당하는 경험이 있나요? 있다면 구체적인 사례를 추가해 주세요.",
                      "보완 행동: 경험 유무를 먼저 확인하세요. 확인 전에는 미보유로 쓰거나 학습이 반드시 필요하다고 판단하지 않습니다."]
        else:
            parts += ["확인 질문: 인용 문장이 이 요건을 충족하는지, 부정 표현·기간·숙련도 조건을 확인해 주세요.",
                      "보완 행동: 요건별 실제 사례와 기간을 추가하세요. 어휘가 겹친다는 이유만으로 충족을 확정하지 않습니다."]
    parts += ["", "공고 원문과 필수·우대 조건을 직접 확인하세요. 입력하지 않은 역량이나 채용 결과를 추정하지 않습니다."]
    return "\n".join(parts)
