"""문서 본문 TF-IDF 코사인 검색. 의미 임베딩 검색은 아니다."""
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone, timedelta, date
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_PATH = DATA_DIR / "jobs.json"
KNOWLEDGE_PATH = DATA_DIR / "knowledge.json"


def load_jobs(path=DATA_PATH):
    with Path(path).open(encoding="utf-8-sig") as stream:
        jobs = json.load(stream)
    if not isinstance(jobs, list) or any(not isinstance(j, dict) for j in jobs):
        raise ValueError("공고 데이터는 객체 배열이어야 합니다.")
    return jobs


def status(job, today=None):
    today = today or datetime.now(timezone(timedelta(hours=9))).date()
    deadline = job.get("deadline", "")
    if not deadline:
        return "마감일 미확인"
    try:
        parsed = date.fromisoformat(deadline)
    except (TypeError, ValueError):
        return "마감일 형식 오류"
    return "마감" if parsed < today else "마감일 기준 유효"


def _features(text):
    tokens = []
    for word in re.findall(r"[a-z0-9가-힣]+", text.casefold()):
        tokens.append("w:" + word)
        tokens.extend("c:" + word[i:i + 2] for i in range(len(word) - 1))
    return Counter(tokens)


def rank_documents(query, documents, limit=4):
    """하드코딩한 직무 키워드가 아니라 전달된 모든 문서 본문을 인덱싱한다."""
    if not documents or not isinstance(query, str) or not query.strip():
        return []
    counts = [_features(doc["title"] + " " + doc["text"]) for doc in documents]
    frequency = Counter(token for count in counts for token in count)
    idf = {t: math.log((len(counts) + 1) / (n + 1)) + 1 for t, n in frequency.items()}
    def vector(count):
        weights = {t: (1 + math.log(n)) * idf[t] for t, n in count.items() if t in idf}
        norm = math.sqrt(sum(w*w for w in weights.values())) or 1
        return {t: w/norm for t, w in weights.items()}
    q = vector(_features(query))
    hits = []
    for doc, count in zip(documents, counts):
        v = vector(count)
        score = sum(weight * v.get(token, 0) for token, weight in q.items())
        if score >= 0.15:
            hits.append({**doc, "score": round(score, 4)})
    return sorted(hits, key=lambda d: (-d["score"], d["id"]))[:max(0, min(limit, 10))]


def search_jobs(query, path=DATA_PATH, limit=3):
    documents = []
    mapping = {}
    for number, job in enumerate(load_jobs(path)):
        state = status(job)
        if state in ("마감", "마감일 형식 오류"):
            continue
        doc_id = str(number)
        mapping[doc_id] = {**job, "deadline_status": state}
        documents.append({"id": doc_id, "title": str(job.get("title", "")),
                          "text": " ".join(str(job.get(k, "")) for k in ("company", "requirements", "description", "skills", "location"))})
    return [mapping[doc["id"]] for doc in rank_documents(query, documents, limit)]


def get_job(job_id, path=DATA_PATH):
    job = next((j for j in load_jobs(path) if j.get("id") == job_id), None)
    return {**job, "deadline_status": status(job)} if job else None


def search_documents(query, knowledge_path=KNOWLEDGE_PATH, jobs_path=DATA_PATH):
    documents = []
    with Path(knowledge_path).open(encoding="utf-8-sig") as stream:
        notes = json.load(stream)
    if not isinstance(notes, list):
        raise ValueError("학습 자료는 배열이어야 합니다.")
    for doc in notes:
        if not isinstance(doc, dict) or not isinstance(doc.get("sections"), list):
            raise ValueError("학습 자료에 sections 배열이 필요합니다.")
        for i, section in enumerate(doc["sections"], 1):
            if not isinstance(section, str) or not section.strip():
                raise ValueError("학습 자료의 문단이 비어 있습니다.")
            documents.append({"id": f"{doc['id']}-{i}", "title": doc["title"], "text": section,
                              "url": doc["url"], "note": doc["note"], "kind": "learning_note"})
    for job in load_jobs(jobs_path):
        # 가상 공고는 실제 정보 검색의 근거에서 제외한다. ID 직접 조회로만 접근 가능하다.
        if str(job.get("id", "")).startswith("SAMPLE-") or "가상" in str(job.get("source", "")):
            continue
        if status(job) in ("마감", "마감일 형식 오류"):
            continue
        documents.append({"id": "job-" + str(job["id"]), "job_id": str(job["id"]), "title": str(job["title"]),
            "text": " ".join(str(job.get(k, "")) for k in ("company", "requirements", "description", "location")),
            "url": str(job.get("source_url", "")), "kind": "job_candidate",
            "note": str(job.get("verification_note", "원문과 현재 모집 여부 미확인")),
            "deadline_status": status(job)})
    if len({d["id"] for d in documents}) != len(documents):
        raise ValueError("문서 ID가 중복되었습니다.")
    return rank_documents(query, documents)
