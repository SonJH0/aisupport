import pytest
from ai import agent
from test_agent_api import FakeClient, completion

@pytest.mark.parametrize('mode', ['auto','json'])
def test_generated_link_filtered_in_actual_response(monkeypatch, mode):
    monkeypatch.setenv('AGENT_TOOL_MODE',mode)
    answer='공식 자료 https://fastapi.tiangolo.com/tutorial/ [backend-1]\n임의 링크 https://example.invalid/made-up'
    responses=[completion(answer)]
    if mode=='json': responses=[completion('{"calls":[]}'), *responses]
    result=agent.respond('Python API 경험의 강점을 분석해 주세요.',client=FakeClient(responses))
    assert 'https://example.invalid' not in result['answer']
    assert 'https://fastapi.tiangolo.com/tutorial/' in result['answer']
    assert result['sources'][0]['id']=='backend-1'


def test_no_sources_means_no_verified_generated_url():
    assert 'https://' not in agent._ground_links('https://example.invalid/test',{})
