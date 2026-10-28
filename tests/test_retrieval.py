import unittest
from datetime import date, timedelta
from unittest.mock import patch
from ai.retrieval import get_job, search_jobs, status

JOBS = [
    {"id":"A","title":"백엔드 개발자","requirements":"Python SQL","source":"가상 예시"},
    {"id":"B","title":"프론트엔드 개발자","requirements":"React","source":"가상 예시"},
    {"id":"OLD","title":"백엔드 개발자","requirements":"Python","deadline":"2000-01-01","source":"가상 예시"},
]

class RetrievalTests(unittest.TestCase):
    @patch("ai.retrieval.load_jobs", return_value=JOBS)
    def test_search_excludes_expired_and_no_match(self, _):
        self.assertEqual([x["id"] for x in search_jobs("Python")], ["A"])
        self.assertEqual(search_jobs("기계학습"), [])
    @patch("ai.retrieval.load_jobs", return_value=JOBS)
    def test_korean_search(self, _):
        self.assertEqual([x["id"] for x in search_jobs("프론트엔드")], ["B"])
    @patch("ai.retrieval.load_jobs", return_value=JOBS)
    def test_get_by_id_reports_expired(self, _):
        self.assertEqual(get_job("OLD")["deadline_status"], "마감")
        self.assertIsNone(get_job("없는공고"))
    def test_deadline_status(self):
        today = date(2026, 1, 10)
        self.assertEqual(status({"deadline":"2026-01-09"}, today), "마감")
        self.assertEqual(status({"deadline":"2026-01-10"}, today), "마감일 기준 유효")
        self.assertEqual(status({}, today), "마감일 미확인")
        self.assertEqual(status({"deadline":"bad"}, today), "마감일 형식 오류")

if __name__ == "__main__":
    unittest.main()
