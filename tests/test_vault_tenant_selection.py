import pytest
from flask import Flask
from unittest.mock import patch

from routes import services, vault


@pytest.mark.parametrize('domain,expected', [
    ('nick.jam-bot.com', 'nick'),
    ('client-12.jam-bot.com', 'client-12'),
    ('NICK.JAM-BOT.COM', 'NICK'),
    ('n.jam-bot.com', 'n'),
    ('nick.jam-bot.com.attacker.test', 'fallback'),
    ('nick.attacker.jam-bot.com', 'fallback'),
    ('https://nick.jam-bot.com', 'fallback'),
    ('attacker.test/nick.jam-bot.com', 'fallback'),
    ('nick.jam-bot.com/path', 'fallback'),
    ('nick.jam-bot.com:443', 'fallback'),
    ('nick.jam-bot.com\n', 'fallback'),
    ('-nick.jam-bot.com', 'fallback'),
    ('nick-.jam-bot.com', 'fallback'),
    ('.jam-bot.com', 'fallback'),
    ('jam-bot.com', 'fallback'),
    ('', 'fallback'),
])
def test_tenant_selection_requires_exact_hostname(monkeypatch, domain, expected):
    monkeypatch.setenv('DOMAIN', domain)
    monkeypatch.setenv('VAULT_USERNAME', 'fallback')
    assert vault._get_username() == expected
    assert services._current_username() == expected


def test_tenant_selection_defaults_to_single_user(monkeypatch):
    monkeypatch.delenv('DOMAIN', raising=False)
    monkeypatch.delenv('VAULT_USERNAME', raising=False)
    assert vault._get_username() == 'default'
    assert services._current_username() == 'default'


@pytest.mark.parametrize('domain,expected', [
    ('nick.jam-bot.com', 'nick'),
    ('nick.jam-bot.com.attacker.test', 'fallback'),
])
def test_vault_route_uses_validated_tenant(monkeypatch, domain, expected):
    monkeypatch.setenv('DOMAIN', domain)
    monkeypatch.setenv('VAULT_USERNAME', 'fallback')
    app = Flask(__name__)
    app.register_blueprint(vault.vault_bp)
    with patch('services.vault.get_credentials_status', return_value=[]) as credentials, \
         patch('services.vault.get_available_models', return_value=[]) as models, \
         patch('services.vault.get_current_model_selection', return_value={}) as selection:
        response = app.test_client().get('/api/vault/credentials')
    assert response.status_code == 200
    credentials.assert_called_once_with(expected)
    models.assert_called_once_with(expected)
    selection.assert_called_once_with(expected)
