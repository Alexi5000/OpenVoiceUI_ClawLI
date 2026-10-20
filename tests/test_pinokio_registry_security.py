import json
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from unittest.mock import patch

import pytest
from flask import Flask
from routes import registry


class CheckinParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.config = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))
        if dict(attrs).get('id') == 'registry-config':
            self.config = json.loads(dict(attrs)['data-config'])


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv('PINOKIO_REGISTRY_URL', raising=False)
    app = Flask(__name__)
    app.register_blueprint(registry.registry_bp)
    return app.test_client()


@pytest.mark.parametrize('url', ['http://127.0.0.1:8080', 'http://169.254.169.254', 'https://api.pinokio.co@evil.test', 'https://evil.test', 'https://api.pinokio.co/../admin'])
def test_request_cannot_select_registry(client, url):
    with patch.object(registry.requests, 'post') as post, patch.object(registry, '_get_git_sha') as sha:
        response = client.post('/checkpoints/snapshot', query_string={'registry': url, 'publish': '1'}, headers={'X-Registry-Token': 'test-token'})
        assert response.status_code == 400
        assert response.json['error'] == 'untrusted_registry'
        post.assert_not_called()
        sha.assert_not_called()
        assert client.get('/registry/checkin', query_string={'registry': url}).status_code == 400


@pytest.mark.parametrize('configured', ['https://api.pinokio.co', 'http://custom-registry:8080/api'])
def test_registry_default_and_operator_configuration(client, monkeypatch, configured):
    monkeypatch.setenv('PINOKIO_REGISTRY_URL', configured)
    with patch.object(registry.requests, 'post') as post, patch.object(registry, '_get_git_sha', return_value='a' * 40):
        post.return_value.status_code = 200
        post.return_value.json.return_value = {}
        response = client.post('/checkpoints/snapshot?publish=1', headers={'X-Registry-Token': 'test-token'})
        assert response.status_code == 200
        assert post.call_args.args[0] == configured + '/checkpoints'
        assert post.call_args.kwargs['headers']['Authorization'] == 'Bearer test-token'
        assert post.call_args.kwargs['allow_redirects'] is False


def test_registry_does_not_follow_real_redirect(client, monkeypatch):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(self.path)
            self.send_response(307)
            self.send_header('Location', '/private-target')
            self.send_header('Content-Length', '0')
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv('PINOKIO_REGISTRY_URL', f'http://127.0.0.1:{server.server_port}')
    try:
        with patch.object(registry, '_get_git_sha', return_value='a' * 40):
            response = client.post('/checkpoints/snapshot?publish=1', headers={'X-Registry-Token': 'test-token'})
        assert response.status_code == 502
        assert received == ['/checkpoints']
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize('url', ['https://evil.test/owner/repo', 'https://github.com/o/repo?path=/admin', 'https://github.com/o/../admin', 'https://github.com/o/repo#fragment'])
def test_github_fallback_rejects_invalid_repository_urls(monkeypatch, url):
    monkeypatch.delenv('GIT_COMMIT', raising=False)
    with patch.object(registry.subprocess, 'check_output', side_effect=OSError), patch.object(registry.os.path, 'exists', return_value=False), patch.object(registry.requests, 'get') as get:
        assert registry._get_git_sha(url) == ''
        get.assert_not_called()


def _no_local_sha(monkeypatch):
    monkeypatch.delenv('GIT_COMMIT', raising=False)
    return (patch.object(registry.subprocess, 'check_output', side_effect=OSError),
            patch.object(registry.os.path, 'exists', return_value=False))


@pytest.mark.parametrize('configured, requested', [
    ('MCERQUA/OpenVoiceUI', 'https://github.com/MCERQUA/OpenVoiceUI'),
    ('MCERQUA/OpenVoiceUI', 'https://github.com/mcerqua/openvoiceui.git'),
    ('owner/legit.name', 'https://github.com/owner/legit.name/'),
])
def test_github_fallback_uses_configured_repository(monkeypatch, configured, requested):
    monkeypatch.setenv('OPENVOICE_GITHUB_REPO', configured)
    a, b = _no_local_sha(monkeypatch)
    with a, b, patch.object(registry.requests, 'get') as get:
        get.return_value.ok = True
        get.return_value.text = 'a' * 40
        assert registry._get_git_sha(requested) == 'a' * 40
        # URL is built only from the fixed prefix and the operator configuration.
        assert get.call_args.args[0] == f'https://api.github.com/repos/{configured}/commits/main'
        assert get.call_args.kwargs['allow_redirects'] is False


def test_github_fallback_default_repository(monkeypatch):
    monkeypatch.delenv('OPENVOICE_GITHUB_REPO', raising=False)
    a, b = _no_local_sha(monkeypatch)
    with a, b, patch.object(registry.requests, 'get') as get:
        get.return_value.ok = True
        get.return_value.text = 'b' * 40
        assert registry._get_git_sha('https://github.com/MCERQUA/OpenVoiceUI') == 'b' * 40
        assert get.call_args.args[0] == 'https://api.github.com/repos/MCERQUA/OpenVoiceUI/commits/main'


@pytest.mark.parametrize('requested', [
    'https://github.com/other/repo',                 # valid shape, not the configured repo
    'https://github.com/MCERQUA/OpenVoiceUI/../x',
    'https://github.com/MCERQUA/OpenVoiceUI%2F..',
    'https://github.com/MCERQUA/OpenVoiceUI/commits',
    'https://github.com/MCERQUA/Open%0aVoiceUI',
    'https://github.com/-bad/repo',
    'https://github.com:443@evil.test/MCERQUA/OpenVoiceUI',
])
def test_github_fallback_rejects_unconfigured_or_malformed_repository(monkeypatch, requested):
    monkeypatch.delenv('OPENVOICE_GITHUB_REPO', raising=False)
    a, b = _no_local_sha(monkeypatch)
    with a, b, patch.object(registry.requests, 'get') as get:
        assert registry._get_git_sha(requested) == ''
        get.assert_not_called()


@pytest.mark.parametrize('configured', ['bad', '../x/y', 'a/b/c', 'owner/..', 'owner/repo?x=1'])
def test_github_fallback_rejects_invalid_configuration(monkeypatch, configured):
    monkeypatch.setenv('OPENVOICE_GITHUB_REPO', configured)
    a, b = _no_local_sha(monkeypatch)
    with a, b, patch.object(registry.requests, 'get') as get:
        assert registry._get_git_sha('https://github.com/' + configured) == ''
        get.assert_not_called()


@pytest.mark.parametrize('url', [
    'javascript:alert(1)', 'data:text/html,<script>alert(1)</script>',
    '//example.test/return', 'https://', 'https://example.test:bad/path',
    'https://example.test/\nreturn', 'https://[invalid/path',
])
def test_checkin_discards_unsafe_return_urls(client, url):
    response = client.get('/registry/checkin', query_string={'return': url})
    assert response.status_code == 200
    assert CheckinParser(response.text).config['returnUrl'] == ''


@pytest.mark.parametrize('url', [
    'http://localhost:5001/complete?key=value&other=1',
    'https://beta.pinokio.co/checkin#complete',
    'https://external.example/return',
])
def test_checkin_preserves_http_return_destinations(client, url):
    response = client.get('/registry/checkin', query_string={'return': url})
    assert response.status_code == 200
    assert CheckinParser(response.text).config['returnUrl'] == url


def test_checkin_health_status_is_plain_text(client):
    from types import SimpleNamespace
    message = '<svg/onload=window.__xss=1>'
    with patch('services.health.health_checker.readiness', return_value=SimpleNamespace(healthy=True, message=message)):
        response = client.get('/registry/checkin')
    assert response.status_code == 200
    assert '&lt;svg/onload=window.__xss=1&gt;' in response.text
    assert message not in response.text


@pytest.mark.parametrize('payload', [
    '</script><script>window.__xss=1</script>',
    '\"><svg/onload=window.__xss=1>',
    "'&quot;&amp;<>& café \u2028 \u2029",
])
def test_checkin_configuration_roundtrips_as_inert_data(client, payload):
    response = client.get('/registry/checkin', query_string={'repo': payload, 'app': payload})
    assert response.status_code == 200
    parsed = CheckinParser(response.text)
    assert parsed.config['repo'] == payload
    assert parsed.config['appSlug'] == payload
    assert sum(tag == 'script' for tag, _ in parsed.elements) == 1
    assert not any(tag == 'svg' for tag, _ in parsed.elements)
    assert not any(key.startswith('on') for _, attrs in parsed.elements for key in attrs)
