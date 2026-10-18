import socket
from unittest.mock import MagicMock, patch

import pytest
from services.public_download import _public_target, _PinnedTLSAdapter, download_public


def _dns(address):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (address, 443))]


@pytest.mark.parametrize('address', ['127.0.0.1', '10.0.0.1', '169.254.169.254', '0.0.0.0', '224.0.0.1'])
def test_private_and_multicast_addresses_are_blocked(address):
    with patch('services.public_download.socket.getaddrinfo', return_value=_dns(address)):
        with pytest.raises(ValueError):
            _public_target('https://media.example/audio.mp3')


def test_dns_binding_preserves_authority_and_certificate_hostname():
    with patch('services.public_download.socket.getaddrinfo', return_value=_dns('93.184.216.34')):
        url, hostname, host = _public_target('https://media.example:8443/audio.mp3?signature=abc')
    assert url == 'https://93.184.216.34:8443/audio.mp3?signature=abc'
    assert hostname == 'media.example'
    assert host == 'media.example:8443'
    adapter = _PinnedTLSAdapter(hostname)
    assert adapter.poolmanager.connection_pool_kw['assert_hostname'] == hostname
    assert adapter.poolmanager.connection_pool_kw['server_hostname'] == hostname


def test_mixed_public_private_dns_answers_are_rejected():
    with patch('services.public_download.socket.getaddrinfo', return_value=_dns('93.184.216.34') + _dns('127.0.0.1')):
        with pytest.raises(ValueError):
            _public_target('https://media.example/audio.mp3')


def _session(response):
    session = MagicMock()
    session.__enter__.return_value = session
    session.get.return_value.__enter__.return_value = response
    return session


def test_redirect_to_internal_address_is_rejected_before_request():
    response = MagicMock(status_code=302, headers={'Location': 'http://127.0.0.1/secret'})
    session = _session(response)
    with patch('services.public_download.socket.getaddrinfo', side_effect=[_dns('93.184.216.34'), _dns('127.0.0.1')]), patch('services.public_download.requests.Session', return_value=session):
        with pytest.raises(ValueError):
            download_public('https://media.example/audio.mp3', max_bytes=100)
    assert session.get.call_count == 1
    assert session.get.call_args.kwargs['allow_redirects'] is False
    assert session.trust_env is False


def test_valid_public_download_and_stream_limit():
    response = MagicMock(status_code=200, headers={})
    response.iter_content.return_value = iter([b'audio'])
    session = _session(response)
    with patch('services.public_download.socket.getaddrinfo', return_value=_dns('93.184.216.34')), patch('services.public_download.requests.Session', return_value=session):
        assert download_public('https://media.example/audio.mp3', max_bytes=5) == b'audio'
        response.iter_content.return_value = iter([b'audio', b'overflow'])
        with pytest.raises(ValueError):
            download_public('https://media.example/audio.mp3', max_bytes=5)
    assert session.get.call_args.args[0].startswith('https://93.184.216.34:443/')
    assert session.get.call_args.kwargs['headers']['Host'] == 'media.example'


def test_provider_host_constraint_and_https_downgrade():
    with pytest.raises(ValueError):
        _public_target('https://bandcamp.com.attacker.example/x', allowed_host_suffix='bandcamp.com')
    with pytest.raises(ValueError):
        _public_target('http://media.example/x', require_https=True)
    with pytest.raises(ValueError):
        _public_target('https://user:password@media.example/x')


def test_suno_callback_preserves_saved_track_and_completion_queue(monkeypatch, tmp_path):
    from flask import Flask
    from routes import suno
    monkeypatch.setattr(suno, 'GENERATED_MUSIC_DIR', tmp_path)
    monkeypatch.setattr(suno, 'GENERATED_METADATA_FILE', tmp_path / 'metadata.json')
    monkeypatch.setattr(suno, 'SUNO_WEBHOOK_SECRET', '')
    monkeypatch.setattr(suno, 'suno_jobs', {'job': {'task_id': 'task', 'status': 'pending', 'prompt': 'hello', 'style': 'jazz'}})
    monkeypatch.setattr(suno, 'completed_songs_queue', [])
    monkeypatch.setattr(suno, '_is_safe_download_url', lambda url: True)
    app = Flask(__name__)
    app.register_blueprint(suno.suno_bp)
    with patch.object(suno, 'download_public', return_value=b'audio') as download:
        response = app.test_client().post('/api/suno/callback', json={
            'code': 200,
            'data': {'callbackType': 'complete', 'task_id': 'task', 'data': [
                {'id': 'song', 'title': 'My Track', 'audio_url': 'https://media.example/track.mp3', 'duration': 10},
            ]},
        })
    assert response.status_code == 200
    download.assert_called_once()
    assert download.call_args.kwargs['require_https'] is True
    assert suno.suno_jobs['job']['status'] == 'complete'
    assert len(suno.completed_songs_queue) == 1
    entry = suno.completed_songs_queue[0]
    assert (tmp_path / entry['filename']).read_bytes() == b'audio'
    assert suno._load_generated_metadata()[entry['filename']]['suno_id'] == 'song'


def test_stem_download_preserves_unicode_names_and_rejects_traversal(monkeypatch, tmp_path):
    from routes import suno
    monkeypatch.setattr(suno, '_stems_dir', lambda: tmp_path)
    monkeypatch.setattr(suno, '_is_safe_download_url', lambda url: True)
    monkeypatch.setattr(suno, '_stem_clear_pending', lambda stem: None)
    with patch.object(suno, 'download_public', return_value=b'audio') as download:
        urls = suno._persist_stem_urls({'vocal': 'https://media.example/a.mp3'}, 'café')
        assert urls['vocal'].endswith('/café-vocal.mp3')
        assert (tmp_path / 'café-vocal.mp3').read_bytes() == b'audio'
        with pytest.raises(ValueError):
            suno._persist_stem_urls({'vocal': 'https://media.example/a.mp3'}, '../escape')
        assert download.call_count == 1
