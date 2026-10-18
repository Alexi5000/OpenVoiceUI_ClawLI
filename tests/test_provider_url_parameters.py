from unittest.mock import patch

import pytest
from flask import Flask
from routes import image_gen, meshy, vision


@pytest.mark.parametrize('model', ['../admin', 'x?key=attacker', 'x#fragment', '//localhost', 'x%2fadmin'])
def test_google_model_path_rejected_before_network(model, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-placeholder')
    with patch.object(image_gen.http, 'post') as post:
        with pytest.raises(ValueError):
            image_gen._generate_gemini(model, 'hello', [])
        with pytest.raises(ValueError):
            image_gen._generate_imagen(model, 'hello')
        with pytest.raises(ValueError):
            vision._gemini_vision('image', 'image/png', 'hello', model)
        post.assert_not_called()


def test_meshy_rejects_task_path_injection(monkeypatch):
    monkeypatch.setattr(meshy, 'MESHY_KEY', 'test-placeholder')
    app = Flask(__name__)
    app.register_blueprint(meshy.meshy_bp)
    with patch.object(meshy.http, 'get') as get:
        client = app.test_client()
        assert client.get('/api/meshy/task/abc?kind=../../admin').status_code == 400
        assert client.get('/api/meshy/task/abc%3Fkey=attacker').status_code == 400
        get.assert_not_called()


def test_google_model_requests_preserve_provider_contract(monkeypatch):
    monkeypatch.setattr(image_gen, 'GEMINI_KEY', 'test-placeholder')
    with patch.object(image_gen.http, 'post') as post:
        post.return_value.json.return_value = {'candidates': [], 'predictions': []}
        image_gen._generate_gemini('gemini-2.5-flash-image', 'hello', [])
        image_gen._generate_imagen('imagen-4.0-generate-001', 'hello')
        assert post.call_count == 2
        for call in post.call_args_list:
            assert 'key=' not in call.args[0]
            assert call.kwargs['headers']['x-goog-api-key'] == 'test-placeholder'
            assert call.kwargs['allow_redirects'] is False


def test_meshy_accepts_provider_task_identifiers(monkeypatch):
    monkeypatch.setattr(meshy, 'MESHY_KEY', 'test-placeholder')
    app = Flask(__name__)
    app.register_blueprint(meshy.meshy_bp)
    with patch.object(meshy.http, 'get') as get:
        get.return_value.json.return_value = {'status': 'IN_PROGRESS', 'progress': 25}
        response = app.test_client().get('/api/meshy/task/task-123?kind=image-to-3d')
        assert response.status_code == 200
        assert get.call_args.args[0] == 'https://api.meshy.ai/openapi/v1/image-to-3d/task-123'
