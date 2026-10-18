import importlib.util
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import quote
from unittest.mock import patch

import pytest
from flask import Flask
from routes import airadio_bridge as radio

spec = importlib.util.spec_from_file_location('booking_security_fixture', Path(__file__).resolve().parents[1] / 'plugins/booking/routes/booking.py')
booking = importlib.util.module_from_spec(spec)
spec.loader.exec_module(booking)


@pytest.fixture
def clients(monkeypatch):
    monkeypatch.setattr(radio, 'AIRADIO_URL', 'https://radio.example')
    monkeypatch.setattr(radio, 'AIRADIO_PUBLIC_FALLBACK', True)
    monkeypatch.setattr(radio, '_effective_user_key', lambda: 'test-radio-key')
    monkeypatch.setattr(booking, '_api_key', lambda: 'test-booking-key')
    monkeypatch.setattr(booking, '_api_url', lambda: 'https://booking.example')
    app = Flask(__name__)
    app.register_blueprint(radio.airadio_bp)
    app.register_blueprint(booking.booking_bp)
    return app.test_client()


@pytest.mark.parametrize('identifier', ['normal-id', 'hello world', 'été目录', 'a?admin=true#fragment', 'literal%2Fvalue', 'name@host:123'])
@pytest.mark.parametrize('provider', ['radio', 'booking'])
def test_provider_ids_remain_path_data(clients, identifier, provider):
    encoded = quote(identifier, safe='')
    with patch.object(radio.http_requests, 'request') as send:
        send.return_value.status_code = 200
        send.return_value.json.return_value = {'ok': True, 'data': {}}
        if provider == 'radio':
            response = clients.get('/api/airadio/catalog/' + encoded)
            expected = 'https://radio.example/api/agent/catalog/' + encoded
        else:
            response = clients.post('/api/booking/bookings/' + encoded + '/cancel', json={'reason': 'requested'})
            expected = 'https://booking.example/v2/bookings/' + encoded + '/cancel'
            assert send.call_args.kwargs['json'] == {'reason': 'requested'}
        assert response.status_code == 200
        assert send.call_args.args[1] == expected
        assert send.call_args.kwargs['allow_redirects'] is False


@pytest.mark.parametrize('identifier', ['.', '..', 'bad\\name', 'bad\x00name'])
@pytest.mark.parametrize('provider', ['radio', 'booking'])
def test_provider_rejects_path_traversal_before_network(clients, identifier, provider):
    encoded = quote(identifier, safe='')
    with patch.object(radio.http_requests, 'request') as send:
        response = (clients.get('/api/airadio/catalog/' + encoded) if provider == 'radio' else clients.post('/api/booking/bookings/' + encoded + '/cancel', json={}))
        assert response.status_code == 400
        send.assert_not_called()


def test_radio_keeps_public_fallback_without_credentials(clients, monkeypatch):
    monkeypatch.setattr(radio, '_effective_user_key', lambda: '')
    monkeypatch.setattr(radio, 'AIRADIO_AGENT_KEY', '')
    with patch.object(radio.http_requests, 'request') as send:
        send.return_value.status_code = 200
        send.return_value.json.return_value = {'ok': True, 'data': {}}
        assert clients.get('/api/airadio/catalog/song%3Fvalue').status_code == 200
        assert send.call_args.args[1] == 'https://radio.example/public/song/song%3Fvalue'
        assert send.call_args.kwargs['headers'] == {}


@pytest.mark.parametrize('provider', ['radio', 'booking'])
def test_provider_does_not_follow_http_redirect(clients, monkeypatch, provider):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            received.append(self.path)
            self.send_response(307)
            self.send_header('Location', '/redirect-target')
            self.send_header('Content-Length', '0')
            self.end_headers()
        do_POST = do_GET

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    monkeypatch.setattr(radio, 'AIRADIO_URL', base)
    monkeypatch.setattr(booking, '_api_url', lambda: base)
    try:
        if provider == 'radio':
            clients.get('/api/airadio/catalog/song')
        else:
            clients.post('/api/booking/bookings/booking/cancel', json={})
        assert len(received) == 1
        assert '/redirect-target' not in received
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
