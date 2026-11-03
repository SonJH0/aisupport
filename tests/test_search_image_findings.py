import base64
from pathlib import Path

import pytest

import ai.retrieval as retrieval
import ai.vision as vision
from ai.web_search import filter_job_results


@pytest.mark.parametrize('url', [
    'https://groupby.kr/jobs/python',
    'https://www.groupby.kr/jobs/backend/?utm_source=test',
    'https://groupby.kr/jobs/react',
    'https://groupby.kr/jobs/frontend',
    'https://groupby.kr/jobs/typescript',
    'https://groupby.kr/jobs/unseen-category?sort=recent',
])
def test_observed_groupby_categories_cannot_be_recommended(url):
    hits, excluded = filter_job_results([{'title': 'Python 백엔드 신입 개발자 채용 공고',
        'url': url, 'description': 'Python FastAPI 신입'}], 'Python FastAPI 신입 백엔드')
    assert not hits
    assert excluded[0]['reason'] == '검색·목록 페이지'


def test_category_fix_does_not_block_all_groupby_paths():
    # 공식 페이지에서 확인한 상세 URL 형태. 제목·요약은 회귀 검사 합성 입력이다.
    hits, _ = filter_job_results([{'title': '테스트 회사 Python 백엔드 신입 채용',
        'url': 'https://groupby.kr/positions/10556', 'description': 'FastAPI'}], 'Python 백엔드 신입')
    assert hits


def test_image_sends_real_bytes_without_unrelated_retrieval(monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-only')
    monkeypatch.setattr(retrieval, 'search_documents', lambda *a: pytest.fail('image-only must not retrieve'))
    raw = (Path(__file__).resolve().parents[1] / 'docs/image-validation/image-01-clear.png').read_bytes()
    captured = {}
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {'content': [{'type': 'text', 'text': '테스트 모델 답변'}]}
    def post(*args, **kwargs):
        captured.update(kwargs['json'])
        return Response()
    monkeypatch.setattr(vision.httpx, 'post', post)
    result = vision.analyze_image('이미지 요건을 읽어 주세요.', 'data:image/png;base64,' + base64.b64encode(raw).decode())
    block = captured['messages'][-1]['content'][0]
    assert block['type'] == 'image'
    assert base64.b64decode(block['source']['data']) == raw
    assert '검색된 학습 자료' not in captured['system']
    assert result['image_analyzed'] is True
    assert result['sources'] == []
    assert result['trace'][0]['status'] == 'skipped_image_only'
