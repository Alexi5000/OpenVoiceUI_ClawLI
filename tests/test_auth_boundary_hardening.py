"""Regression tests for the 2026-10-23 auth-boundary hardening.

Covers:
  * /ws/browse-stream honours the same Clerk predicate as create_app (incl. the
    VITE_CLERK_PUBLISHABLE_KEY alias),
  * Origin binding on cookie-authenticated WebSocket upgrades,
  * Suno callback authentication (shared token / HMAC, fail-closed under Clerk),
  * GET /api/suno only exempts read-only actions,
  * /api/theme writes require auth while GET stays public.
"""
import ast
import hashlib
import hmac
import json
import logging
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from flask import Flask, request

from app import create_app

_CLERK_VARS = (
    'CLERK_PUBLISHABLE_KEY', 'VITE_CLERK_PUBLISHABLE_KEY', 'CLERK_SECRET_KEY',
    'CANVAS_REQUIRE_AUTH', 'AGENT_API_KEY', 'WS_ALLOWED_ORIGINS', 'CORS_ORIGINS',
)


@pytest.fixture(autouse=True)
def _clean_auth_env(monkeypatch):
    for var in _CLERK_VARS:
        monkeypatch.delenv(var, raising=False)
    from services import auth
    monkeypatch.setattr(
        auth, 'verify_clerk_token',
        lambda token: {'user-token': 'user', 'admin-token': 'admin'}.get(token),
    )
    monkeypatch.setattr(auth, 'is_admin_user', lambda user: user == 'admin')


def _load_handler(name, **extra):
    source = Path(__file__).parents[1] / 'server.py'
    node = next(n for n in ast.parse(source.read_text()).body
                if isinstance(n, ast.FunctionDef) and n.name == name)
    node.decorator_list = []
    scope = {'os': os, 'json': json, 'logger': logging.getLogger(__name__), 'request': request}
    scope.update(extra)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), scope)
    return scope[name]


def _call(handler, headers=None, path='/ws/x', query=''):
    ws = Mock()
    app = Flask(__name__)
    with app.test_request_context(path + query, base_url='https://voice.example', headers=headers or {}):
        handler(ws)
    return ws


def _messages(ws):
    return [json.loads(c.args[0])['message'] for c in ws.send.call_args_list]


# ---------------------------------------------------------------------------
# 1. Browse WebSocket uses the shared Clerk predicate
# ---------------------------------------------------------------------------

@pytest.fixture
def browse(monkeypatch):
    runner = Mock()
    asyncio_stub = Mock(run=runner)
    handler = _load_handler('browse_stream_websocket', asyncio=asyncio_stub, websockets=Mock())

    def _run(headers=None, query=''):
        runner.reset_mock()
        ws = _call(handler, headers, '/ws/browse-stream', query)
        # asyncio.run() is the upstream connection; closing the coroutine
        # avoids "never awaited" warnings.
        for c in runner.call_args_list:
            c.args[0].close()
        return ws, runner.called
    return _run


@pytest.mark.parametrize('env', [
    {'VITE_CLERK_PUBLISHABLE_KEY': 'pk_test_alias'},
    {'CLERK_PUBLISHABLE_KEY': 'pk_test_canonical'},
    {'CLERK_SECRET_KEY': 'sk_test_secret'},
    {'CANVAS_REQUIRE_AUTH': 'true'},
])
def test_browse_stream_rejects_anonymous_for_every_clerk_config(browse, monkeypatch, env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    ws, connected = browse()
    assert not connected
    assert _messages(ws) == ['Unauthorized']
    ws.close.assert_called()


def test_browse_stream_alias_config_accepts_valid_session_and_agent_key(browse, monkeypatch):
    monkeypatch.setenv('VITE_CLERK_PUBLISHABLE_KEY', 'pk_test_alias')
    monkeypatch.setenv('AGENT_API_KEY', 'agent-key')
    assert browse({'Cookie': '__session=user-token'})[1]
    assert browse({'X-Agent-Key': 'agent-key'})[1]
    assert not browse({'X-Agent-Key': 'wrong'})[1]
    assert not browse({'Cookie': '__session=forged'})[1]


def test_browse_stream_local_mode_stays_open(browse):
    assert browse()[1]


def test_app_and_handler_share_clerk_predicate(monkeypatch):
    from services.auth import clerk_auth_enabled
    assert not clerk_auth_enabled()
    monkeypatch.setenv('VITE_CLERK_PUBLISHABLE_KEY', '  ')
    assert not clerk_auth_enabled()
    monkeypatch.setenv('VITE_CLERK_PUBLISHABLE_KEY', 'pk_test_alias')
    assert clerk_auth_enabled()


# ---------------------------------------------------------------------------
# 2. Origin binding on cookie-authenticated WebSockets
# ---------------------------------------------------------------------------

_FOREIGN = ['https://evil.example', 'http://voice.example', 'https://voice.example.evil.example',
            'null', 'https://voice.example/path', 'https://user@voice.example', 'https://[']


@pytest.mark.parametrize('name', ['clawdbot_websocket', 'openclaw_ui_websocket', 'xai_realtime_websocket'])
@pytest.mark.parametrize('origin', _FOREIGN)
def test_cookie_websockets_reject_foreign_origin(monkeypatch, name, origin):
    monkeypatch.setenv('CLAWDBOT_AUTH_TOKEN', 'gateway-secret')
    monkeypatch.setenv('XAI_API_KEY', 'xai-secret')
    from services import auth
    verify = Mock(return_value='admin')
    monkeypatch.setattr(auth, 'verify_clerk_token', verify)
    handler = _load_handler(name)
    ws = _call(handler, {'Origin': origin, 'Cookie': '__session=admin-token'})
    assert _messages(ws) == ['Unauthorized']
    verify.assert_not_called()
    ws.close.assert_called_once()


@pytest.mark.parametrize('name,next_error', [
    ('clawdbot_websocket', 'Server configuration error'),
    ('xai_realtime_websocket', 'xAI API key not configured on server'),
])
@pytest.mark.parametrize('origin', [None, 'https://voice.example', 'https://VOICE.example'])
def test_cookie_websockets_accept_same_origin(monkeypatch, name, next_error, origin):
    monkeypatch.delenv('CLAWDBOT_AUTH_TOKEN', raising=False)
    monkeypatch.delenv('XAI_API_KEY', raising=False)
    handler = _load_handler(name)
    headers = {'Cookie': '__session=admin-token'}
    if origin:
        headers['Origin'] = origin
    ws = _call(handler, headers)
    # Passed both the Origin and Clerk gates; stopped at the next config check.
    assert _messages(ws) == [next_error]


def test_browse_stream_rejects_foreign_origin_even_in_local_mode(browse):
    ws, connected = browse({'Origin': 'https://evil.example'})
    assert not connected
    assert _messages(ws) == ['Unauthorized']
    assert browse({'Origin': 'https://voice.example'})[1]


def test_global_hook_blocks_cross_origin_websocket_upgrades(monkeypatch):
    app, _ = create_app({'TESTING': True, 'RATELIMIT_ENABLED': False})

    @app.get('/ws/probe')
    def probe():
        return 'reached'

    client = app.test_client()
    up = {'Upgrade': 'websocket'}
    host = {'base_url': 'https://voice.example'}
    assert client.get('/ws/probe', headers={**up, 'Origin': 'https://evil.example'}, **host).status_code == 403
    assert client.get('/ws/probe', headers={**up, 'Origin': 'https://voice.example'}, **host).status_code == 200
    assert client.get('/ws/probe', headers=up, **host).status_code == 200
    # Plain (non-upgrade) GETs are unaffected by the WebSocket binding.
    assert client.get('/ws/probe', headers={'Origin': 'https://evil.example'}, **host).status_code == 200


def test_websocket_extra_origins_are_opt_in(monkeypatch):
    monkeypatch.setenv('WS_ALLOWED_ORIGINS', 'https://companion.example, https://two.example/')
    app, _ = create_app({'TESTING': True, 'RATELIMIT_ENABLED': False})

    @app.get('/ws/probe')
    def probe():
        return 'reached'

    client = app.test_client()
    up = {'Upgrade': 'websocket'}
    for origin, code in [('https://companion.example', 200), ('https://two.example', 200),
                         ('https://three.example', 403)]:
        assert client.get('/ws/probe', headers={**up, 'Origin': origin},
                          base_url='https://voice.example').status_code == code


# ---------------------------------------------------------------------------
# 3. Suno callback authentication
# ---------------------------------------------------------------------------

_ERROR_EVENT = {'code': 200, 'data': {'callbackType': 'error', 'taskId': 'dummy-task',
                                       'errorMessage': 'fixture'}}


@pytest.fixture
def suno_app(monkeypatch, tmp_path):
    from routes import suno
    monkeypatch.setattr(suno, 'GENERATED_MUSIC_DIR', tmp_path)
    monkeypatch.setattr(suno, 'GENERATED_METADATA_FILE', tmp_path / 'metadata.json')
    monkeypatch.setattr(suno, 'suno_jobs', {})
    monkeypatch.setattr(suno, 'completed_songs_queue', [])
    monkeypatch.setattr(suno, 'failed_songs_queue', [])
    monkeypatch.setattr(suno, 'SUNO_API_KEY', 'dummy-suno-key')
    monkeypatch.setattr(suno, 'SUNO_CALLBACK_TOKENS_FILE', tmp_path / 'cb-tokens.json')
    monkeypatch.setattr(suno, 'SUNO_CALLBACK_URL', 'https://voice.example/api/suno/callback')

    def build():
        app, _ = create_app({'TESTING': True, 'RATELIMIT_ENABLED': False})
        app.register_blueprint(suno.suno_bp)
        return app.test_client()
    return suno, build


def test_unsigned_callback_rejected_when_clerk_enabled_without_secret(suno_app, monkeypatch):
    suno, build = suno_app
    monkeypatch.setenv('VITE_CLERK_PUBLISHABLE_KEY', 'pk_test_alias')
    monkeypatch.setattr(suno, 'SUNO_WEBHOOK_SECRET', '')
    r = build().post('/api/suno/callback', json=_ERROR_EVENT)
    assert r.status_code == 403
    assert suno.failed_songs_queue == []


def test_callback_with_secret_requires_token_or_signature(suno_app, monkeypatch):
    suno, build = suno_app
    monkeypatch.setenv('CLERK_PUBLISHABLE_KEY', 'pk_test_canonical')
    monkeypatch.setattr(suno, 'SUNO_WEBHOOK_SECRET', 'webhook-secret')
    client = build()
    assert client.post('/api/suno/callback', json=_ERROR_EVENT).status_code == 403
    assert client.post('/api/suno/callback?token=wrong', json=_ERROR_EVENT).status_code == 403
    assert client.post('/api/suno/callback', json=_ERROR_EVENT,
                       headers={'X-Suno-Signature': 'bad'}).status_code == 403
    assert client.post('/api/suno/callback?token=webhook-secret', json=_ERROR_EVENT).status_code == 403
    assert suno.failed_songs_queue == []

    token = suno._callback_token()
    assert client.post(f'/api/suno/callback?token={token}', json=_ERROR_EVENT).status_code == 200
    assert len(suno.failed_songs_queue) == 1

    body = json.dumps(_ERROR_EVENT).encode()
    sig = hmac.new(b'webhook-secret', body, hashlib.sha256).hexdigest()
    assert client.post('/api/suno/callback', data=body, content_type='application/json',
                       headers={'X-Suno-Signature': sig}).status_code == 200


def _cb_token(url):
    from urllib.parse import parse_qs, urlsplit
    return parse_qs(urlsplit(url).query)['cb'][0]


def test_callback_url_carries_fresh_per_request_token(suno_app, monkeypatch):
    suno, _ = suno_app
    for secret in ('', 'webhook-secret'):
        monkeypatch.setattr(suno, 'SUNO_WEBHOOK_SECRET', secret)
        u1, u2 = suno._callback_url(), suno._callback_url()
        assert u1.startswith('https://voice.example/api/suno/callback?cb=')
        assert _cb_token(u1) != _cb_token(u2)
        assert len(_cb_token(u1)) >= 40
        assert 'webhook-secret' not in u1
    # Only hashes are stored, never the token itself.
    raw = (suno.SUNO_CALLBACK_TOKENS_FILE).read_text()
    assert _cb_token(u1) not in raw


def test_callback_url_without_configured_url_is_unchanged(suno_app, monkeypatch):
    suno, _ = suno_app
    monkeypatch.setattr(suno, 'SUNO_CALLBACK_URL', '')
    assert suno._callback_url() == ''


def test_per_request_token_authenticates_callback_without_secret(suno_app, monkeypatch):
    suno, build = suno_app
    monkeypatch.setenv('VITE_CLERK_PUBLISHABLE_KEY', 'pk_test_alias')
    monkeypatch.setattr(suno, 'SUNO_WEBHOOK_SECRET', '')
    client = build()
    token = _cb_token(suno._callback_url())
    assert client.post('/api/suno/callback?cb=forged', json=_ERROR_EVENT).status_code == 403
    assert suno.failed_songs_queue == []
    assert client.post(f'/api/suno/callback?cb={token}', json=_ERROR_EVENT).status_code == 200
    assert len(suno.failed_songs_queue) == 1
    # Repeated callbacks for the same task (text/first/complete stages) are fine.
    assert client.post(f'/api/suno/callback?cb={token}', json=_ERROR_EVENT).status_code == 200


def test_per_request_token_is_bound_to_first_task_id(suno_app, monkeypatch):
    suno, build = suno_app
    monkeypatch.setenv('CLERK_PUBLISHABLE_KEY', 'pk_test_canonical')
    monkeypatch.setattr(suno, 'SUNO_WEBHOOK_SECRET', '')
    client = build()
    token = _cb_token(suno._callback_url())
    assert client.post(f'/api/suno/callback?cb={token}', json=_ERROR_EVENT).status_code == 200
    other = {'code': 200, 'data': {'callbackType': 'error', 'task_id': 'other-task',
                                    'errorMessage': 'fixture'}}
    assert client.post(f'/api/suno/callback?cb={token}', json=other).status_code == 403
    assert len(suno.failed_songs_queue) == 1


def test_expired_per_request_token_is_rejected(suno_app, monkeypatch):
    suno, build = suno_app
    monkeypatch.setenv('CLERK_PUBLISHABLE_KEY', 'pk_test_canonical')
    monkeypatch.setattr(suno, 'SUNO_WEBHOOK_SECRET', '')
    token = _cb_token(suno._callback_url())
    real_time = suno.time.time
    monkeypatch.setattr(suno.time, 'time', lambda: real_time() + suno._CALLBACK_TOKEN_TTL_S + 1)
    assert build().post(f'/api/suno/callback?cb={token}', json=_ERROR_EVENT).status_code == 403
    assert suno.failed_songs_queue == []


def test_generate_request_sends_tokenized_callback(suno_app, monkeypatch):
    suno, build = suno_app
    monkeypatch.setattr(suno, 'SUNO_WEBHOOK_SECRET', '')
    with patch.object(suno.http_requests, 'post', side_effect=suno.http_requests.RequestException('stub')) as post:
        build().post('/api/suno', json={'action': 'generate', 'prompt': 'dummy'})
    assert post.called
    sent = post.call_args.kwargs['json']['callBackUrl']
    assert suno._verify_callback_token(_cb_token(sent), 'dummy-task')


def test_unsigned_callback_still_accepted_in_local_mode(suno_app, monkeypatch):
    suno, build = suno_app
    monkeypatch.setattr(suno, 'SUNO_WEBHOOK_SECRET', '')
    assert build().post('/api/suno/callback', json=_ERROR_EVENT).status_code == 200
    assert len(suno.failed_songs_queue) == 1


# ---------------------------------------------------------------------------
# 4. GET /api/suno only exempts read-only actions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('query', ['action=generate&prompt=dummy', 'action=jingle&prompt=dummy',
                                   'action=credits', 'action=status&job_id=x', 'action=extend'])
def test_anonymous_get_cannot_dispatch_suno_work(suno_app, monkeypatch, query):
    suno, build = suno_app
    monkeypatch.setenv('VITE_CLERK_PUBLISHABLE_KEY', 'pk_test_alias')
    with patch.object(suno.http_requests, 'post') as post, patch.object(suno.http_requests, 'get') as get:
        r = build().get(f'/api/suno?{query}')
    assert r.status_code == 401
    post.assert_not_called()
    get.assert_not_called()


@pytest.mark.parametrize('query', ['', 'action=list', 'action=list_jingles', 'action=jingle_styles'])
def test_read_only_suno_gets_stay_public(suno_app, monkeypatch, query):
    _, build = suno_app
    monkeypatch.setenv('CLERK_PUBLISHABLE_KEY', 'pk_test_canonical')
    assert build().get(f'/api/suno?{query}').status_code == 200


def test_authenticated_get_generate_still_dispatches(suno_app, monkeypatch):
    suno, build = suno_app
    monkeypatch.setenv('CLERK_PUBLISHABLE_KEY', 'pk_test_canonical')
    monkeypatch.setenv('AGENT_API_KEY', 'agent-key')
    for headers in ({'Authorization': 'Bearer user-token'}, {'X-Agent-Key': 'agent-key'}):
        with patch.object(suno.http_requests, 'post',
                          side_effect=suno.http_requests.RequestException('stub')) as post:
            build().get('/api/suno?action=generate&prompt=dummy', headers=headers)
        post.assert_called_once()


def test_local_mode_get_generate_unchanged(suno_app):
    suno, build = suno_app
    with patch.object(suno.http_requests, 'post',
                      side_effect=suno.http_requests.RequestException('stub')) as post:
        build().get('/api/suno?action=generate&prompt=dummy')
    post.assert_called_once()


# ---------------------------------------------------------------------------
# 5. Theme writes require auth; reads stay public
# ---------------------------------------------------------------------------

@pytest.fixture
def theme_client(monkeypatch, tmp_path):
    from routes import theme
    theme_file = tmp_path / 'theme.json'
    theme_file.write_text(json.dumps({'primary': '#000000', 'accent': '#ffffff'}))
    monkeypatch.setattr(theme, 'THEME_FILE', theme_file)

    def build():
        app, _ = create_app({'TESTING': True, 'RATELIMIT_ENABLED': False})
        app.register_blueprint(theme.theme_bp)
        return app.test_client()
    return theme_file, build


def test_theme_writes_require_auth_when_clerk_enabled(theme_client, monkeypatch):
    theme_file, build = theme_client
    monkeypatch.setenv('VITE_CLERK_PUBLISHABLE_KEY', 'pk_test_alias')
    before = theme_file.read_text()
    client = build()
    assert client.post('/api/theme', json={'primary': '#112233', 'accent': '#445566'}).status_code == 401
    assert client.post('/api/theme/reset').status_code == 401
    assert theme_file.read_text() == before
    assert client.get('/api/theme').status_code == 200
    assert client.head('/api/theme').status_code == 200

    r = client.post('/api/theme', json={'primary': '#112233', 'accent': '#445566'},
                    headers={'Authorization': 'Bearer user-token'})
    assert r.status_code == 200
    assert json.loads(theme_file.read_text())['primary'] == '#112233'


def test_theme_writes_open_in_local_mode(theme_client):
    theme_file, build = theme_client
    assert build().post('/api/theme', json={'primary': '#112233', 'accent': '#445566'}).status_code == 200
    assert json.loads(theme_file.read_text())['accent'] == '#445566'


@pytest.mark.parametrize('name', ['clawdbot_websocket', 'openclaw_ui_websocket', 'xai_realtime_websocket'])
def test_origin_rejection_log_excludes_request_values(caplog, name):
    handler = _load_handler(name)
    with caplog.at_level(logging.WARNING):
        _call(handler, {'Origin': 'https://evil.example/INJECTED'}, path='/ws/x%0D%0AFORGED')
    text = '\n'.join(r.getMessage() for r in caplog.records)
    assert 'rejected: cross-origin upgrade' in text
    for marker in ('FORGED', 'INJECTED', '\r', 'evil.example'):
        assert marker not in text
