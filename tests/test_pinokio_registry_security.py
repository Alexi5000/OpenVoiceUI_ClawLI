from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from unittest.mock import patch

import pytest
from flask import Flask
from routes import registry


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


def test_github_fallback_preserves_repository_name(monkeypatch):
    monkeypatch.delenv('GIT_COMMIT', raising=False)
    with patch.object(registry.subprocess, 'check_output', side_effect=OSError), patch.object(registry.os.path, 'exists', return_value=False), patch.object(registry.requests, 'get') as get:
        get.return_value.ok = True
        get.return_value.text = 'a' * 40
        assert registry._get_git_sha('https://github.com/owner/legit.git') == 'a' * 40
        assert get.call_args.args[0] == 'https://api.github.com/repos/owner/legit/commits/main'
        assert get.call_args.kwargs['allow_redirects'] is False
