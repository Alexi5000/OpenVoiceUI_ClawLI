from unittest.mock import Mock, patch

import pytest
import requests

from app import create_app
from routes import canvas


@pytest.mark.parametrize('mime', ['text/html', 'image/svg+xml', 'application/xhtml+xml', 'text/javascript'])
def test_preview_isolation_applies_to_all_content_types(mime):
    app, _ = create_app({'TESTING': True})
    app.register_blueprint(canvas.canvas_bp)
    response = requests.Response()
    response.status_code = 200
    response._content = b'<script>window.example = true</script>'
    response.headers = {'content-type': mime, 'Set-Cookie': 'session=evil',
                        'Location': '/admin', 'Refresh': '0; url=/admin',
                        'Content-Security-Policy': 'sandbox allow-same-origin',
                        'Access-Control-Allow-Credentials': 'true'}
    response.iter_content = Mock(return_value=[response.content])
    with patch.object(canvas.http_requests, 'get', return_value=response):
        result = app.test_client().get('/website-dev/example')
    assert result.status_code == 200
    assert result.headers['Content-Security-Policy'] == 'sandbox allow-scripts'
    assert result.headers['Access-Control-Allow-Origin'] == '*'
    assert b'window.example' in result.data
    for header in ('Set-Cookie', 'Location', 'Refresh', 'Access-Control-Allow-Credentials'):
        assert header not in result.headers


@pytest.mark.parametrize('method', ['POST', 'PUT', 'PATCH', 'DELETE'])
def test_opaque_origin_cannot_write_to_parent_even_without_clerk(method):
    app, _ = create_app({'TESTING': True})
    called = []
    @app.route('/private-write', methods=[method])
    def write():
        called.append(True)
        return 'okay'
    client = app.test_client()
    assert client.open('/private-write', method=method, headers={'Origin': 'null'}).status_code == 403
    assert called == []
    assert client.open('/private-write', method=method).status_code == 200
    assert called == [True]


def test_preview_module_preflight_is_noncredentialed():
    app, _ = create_app({'TESTING': True})
    app.register_blueprint(canvas.canvas_bp)
    result = app.test_client().options('/website-dev/api', headers={'Origin': 'null'})
    assert result.status_code == 204
    assert result.headers['Access-Control-Allow-Origin'] == '*'
    assert result.headers['Access-Control-Allow-Headers'] == 'Content-Type'
    assert 'Access-Control-Allow-Credentials' not in result.headers
