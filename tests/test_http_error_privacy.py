from unittest.mock import Mock

import pytest
from flask import Flask

from routes import maps, onboarding


@pytest.mark.parametrize('method', ['get', 'post'])
def test_onboarding_errors_do_not_disclose_exception_text(monkeypatch, method):
    path = Mock()
    path.exists.return_value = True
    path.read_text.side_effect = RuntimeError('/private/config token=secret-sentinel')
    path.write_text.side_effect = RuntimeError('/private/config token=secret-sentinel')
    monkeypatch.setattr(onboarding, 'STATE_FILE', path)
    app = Flask(__name__)
    app.register_blueprint(onboarding.onboarding_bp)
    response = getattr(app.test_client(), method)('/api/onboarding/state', json={})
    assert response.status_code == 500
    assert response.json == {'error': 'Request failed.'}


def test_maps_error_does_not_disclose_request_key(monkeypatch):
    monkeypatch.setenv('GOOGLE_MAPS_API_KEY', 'test-key')
    monkeypatch.setattr(maps.http, 'get', Mock(side_effect=RuntimeError('https://provider/?key=secret-sentinel')))
    app = Flask(__name__)
    app.register_blueprint(maps.maps_bp)
    response = app.test_client().post('/api/maps/directions', json={'origin': 'A', 'destination': 'B'})
    assert response.status_code == 502
    assert response.json == {'ok': False, 'error': 'directions lookup failed'}


def test_onboarding_success_keeps_payload(tmp_path, monkeypatch):
    monkeypatch.setattr(onboarding, 'STATE_FILE', tmp_path / 'state.json')
    app = Flask(__name__)
    app.register_blueprint(onboarding.onboarding_bp)
    client = app.test_client()
    assert client.post('/api/onboarding/state', json={'step': 2}).json == {'ok': True}
    assert client.get('/api/onboarding/state').json == {'step': 2}
