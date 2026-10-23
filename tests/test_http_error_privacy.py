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


def test_credential_test_route_hides_provider_exception(monkeypatch):
    from routes import vault as route
    from services import vault
    import requests
    monkeypatch.setattr(route, '_get_username', lambda: 'test')
    monkeypatch.setattr(vault, 'get_catalog_credential', lambda _: {'test': {'url': 'https://provider.test'}})
    monkeypatch.setattr(vault, 'read_vault', lambda _: {'credentials': {'demo': {'value': 'test-key'}}})
    monkeypatch.setattr(requests, 'request', Mock(side_effect=requests.ConnectionError('/private token=secret-sentinel')))
    app = Flask(__name__)
    app.register_blueprint(route.vault_bp)
    response = app.test_client().post('/api/vault/credentials/demo/test')
    assert response.status_code == 200
    assert response.json == {'ok': False, 'message': 'Connection failed'}


def test_unreadable_job_route_hides_exception_but_keeps_failed_state(monkeypatch):
    from routes import tools
    from services import tool_jobs
    path = Mock()
    path.exists.return_value = True
    monkeypatch.setattr(tool_jobs, '_path', lambda _: path)
    monkeypatch.setattr(tool_jobs, 'open', Mock(side_effect=OSError('/private token=secret-sentinel')), raising=False)
    app = Flask(__name__)
    app.register_blueprint(tools.tools_bp)
    response = app.test_client().get('/api/tools/jobs/job-1')
    assert response.status_code == 200
    assert response.json == {'id': 'job-1', 'status': 'failed', 'error': 'job file unreadable'}


def test_import_failure_preserves_counts_without_exception_text(tmp_path, monkeypatch):
    from services import chatgpt_parser
    monkeypatch.setattr(chatgpt_parser, '_extract_conversations_json', lambda _: '[{"title":"a"}]')
    monkeypatch.setattr(chatgpt_parser, '_process_conversation', Mock(side_effect=OSError('/private token=secret-sentinel')))
    result = chatgpt_parser.parse_chatgpt_export(tmp_path / 'input.zip', tmp_path / 'output')
    assert result['total'] == 1
    assert result['imported'] == 0
    assert result['skipped'] == 1
    assert result['errors'] == ['Error processing conversation']


def test_plugin_config_route_hides_indirect_exception(monkeypatch):
    from routes import plugins as route
    from services import plugins
    monkeypatch.setitem(plugins._registry, 'demo', {'lifecycle': {'post_install': {'requires_container': True, 'provision': 'demo'}}})
    monkeypatch.setattr(plugins, '_get_username', lambda: 'test')
    monkeypatch.setattr(plugins.requests, 'put', Mock(side_effect=RuntimeError('/private token=secret-sentinel')))
    app = Flask(__name__)
    app.register_blueprint(route.plugins_bp)
    response = app.test_client().put('/api/plugins/demo/config', json={'config': {'enabled': True}})
    assert response.status_code == 500
    assert response.json == {'error': 'Plugin operation failed'}


def test_bridge_failure_keeps_status_and_code_without_exception(monkeypatch):
    from routes import airadio_bridge
    import requests
    monkeypatch.setattr(airadio_bridge.http_requests, 'request', Mock(side_effect=requests.ConnectionError('/private token=secret-sentinel')))
    result = airadio_bridge._airadio_call('GET', '/api/songs')
    app = Flask(__name__)
    with app.app_context():
        response, status = airadio_bridge._bridge_response(result)
        assert status == 502
        assert response.json['error'] == {'code': 'BRIDGE_UNREACHABLE', 'message': 'Could not reach AI-Radio'}
        assert response.json['ok'] is False


def test_update_verification_hides_subprocess_output(tmp_path, monkeypatch):
    from services import update_manager
    monkeypatch.setattr(update_manager.subprocess, 'run', Mock(return_value=Mock(returncode=1, stdout='secret-sentinel', stderr='/private/secret-sentinel')))
    result = update_manager.UpdateManager(tmp_path).verify()
    assert result == {'healthy': False, 'errors': ['Import check failed', 'Dependency issues detected']}
