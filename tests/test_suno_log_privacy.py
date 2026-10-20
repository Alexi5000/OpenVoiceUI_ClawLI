import logging
from unittest.mock import Mock

import pytest
from flask import Flask


@pytest.mark.parametrize('helper', ['_submit_suno_job', '_submit_process_job'])
@pytest.mark.parametrize('status', [200, 400])
def test_submission_logs_metadata_without_payloads(monkeypatch, caplog, helper, status):
    from routes import suno

    body = {'uploadUrl': 'https://media.example/audio?token=private-request-marker'}
    response = Mock(status_code=status, text='private-response-marker')
    response.json.return_value = {'code': 200, 'data': {'taskId': 'task'}}
    post = Mock(return_value=response)
    monkeypatch.setattr(suno.http_requests, 'post', post)
    monkeypatch.setattr(suno, 'suno_jobs', {})
    monkeypatch.setattr(suno, 'SUNO_CALLBACK_URL', '')
    monkeypatch.setattr(suno, '_provider_receipt', Mock())
    monkeypatch.setattr(suno, '_task_log', Mock())
    with Flask(__name__).app_context(), caplog.at_level(logging.INFO, logger=suno.__name__):
        result = getattr(suno, helper)('/api/v1/generate', body, 'extend').get_json()
    assert post.call_args.kwargs['json'] == body
    assert result['action'] == ('generating' if status == 200 else 'error')
    assert 'private-request-marker' not in caplog.text
    assert 'private-response-marker' not in caplog.text
    assert f'response: {status}' in caplog.text
    assert '(1 fields)' in caplog.text


def test_jingle_logs_do_not_copy_brand_or_prompt(monkeypatch, caplog):
    from routes import suno

    response = Mock(status_code=400, text='private-response-marker')
    post = Mock(return_value=response)
    monkeypatch.setattr(suno.http_requests, 'post', post)
    with Flask(__name__).app_context(), caplog.at_level(logging.INFO, logger=suno.__name__):
        result = suno._action_jingle(lambda key: None, {
            'brand': 'private-brand-marker', 'style': 'private-style-marker',
        }).get_json()
    assert result['action'] == 'error'
    assert 'private-brand-marker' in post.call_args.kwargs['json']['prompt']
    assert 'private-brand-marker' not in caplog.text
    assert 'private-style-marker' not in caplog.text
    assert 'private-response-marker' not in caplog.text
    assert 'Suno jingle:' in caplog.text
