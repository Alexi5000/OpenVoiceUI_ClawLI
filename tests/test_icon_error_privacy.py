import base64
import json
from unittest.mock import Mock

import pytest
import requests
from flask import Flask


@pytest.mark.parametrize('failure', ['http', 'connection', 'timeout'])
def test_icon_provider_failure_does_not_return_credentials(monkeypatch, caplog, failure):
    from routes import icons

    secret = 'synthetic-private-provider-marker'
    url = f'https://provider.invalid/generate?key={secret}'
    response = requests.Response()
    response.status_code = 403
    response.url = url
    post = Mock(return_value=response)
    if failure == 'connection':
        post.side_effect = requests.ConnectionError(f'Cannot connect to {url}')
    elif failure == 'timeout':
        post.side_effect = requests.Timeout(f'Timeout reaching {url}')
    monkeypatch.setattr(icons, 'GEMINI_API_KEY', secret)
    monkeypatch.setattr(icons.requests, 'post', post)
    monkeypatch.setattr(icons, 'search_global_icons', Mock(return_value=[]))
    app = Flask(__name__)
    app.register_blueprint(icons.icons_bp)
    result = app.test_client().post('/api/icons/generate', json={'prompt': 'a blue circle'})
    assert result.status_code == 502
    assert result.get_json() == {'error': 'Gemini icon generation failed; retry shortly'}
    assert secret not in result.get_data(as_text=True)
    assert secret not in caplog.text
    assert secret in post.call_args.args[0]


def test_successful_icon_generation_retains_image_and_metadata(monkeypatch, tmp_path):
    from routes import icons
    from services import metered_spend

    image = b'synthetic-image-bytes'
    response = Mock()
    response.json.return_value = {'candidates': [{'content': {'parts': [{'inlineData': {
        'data': base64.b64encode(image).decode(), 'mimeType': 'image/png',
    }}]}}]}
    monkeypatch.setattr(icons, 'GEMINI_API_KEY', 'synthetic-private-provider-marker')
    monkeypatch.setattr(icons.requests, 'post', Mock(return_value=response))
    monkeypatch.setattr(icons, 'search_global_icons', Mock(return_value=[]))
    monkeypatch.setattr(icons, '_remove_background', lambda data: data)
    monkeypatch.setattr(icons, '_ensure_generated_dir', lambda: tmp_path)
    monkeypatch.setattr(metered_spend, 'log_spend', Mock())
    result = icons.generate_icon_image('a blue circle', name='circle')
    assert result['url'] == '/api/icons/generated/circle.png'
    assert (tmp_path / 'circle.png').read_bytes() == image
    assert json.loads((tmp_path / 'circle.png.meta.json').read_text())['prompt'] == 'a blue circle'
    metered_spend.log_spend.assert_called_once_with('icons/generate', icons.GEMINI_MODEL)
