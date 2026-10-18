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
