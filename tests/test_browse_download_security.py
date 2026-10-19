from types import SimpleNamespace

import pytest
import requests
from flask import Flask

from routes import browse
from services import paths


@pytest.fixture
def download_env(tmp_path, monkeypatch):
    uploads = tmp_path / 'uploads'
    uploads.mkdir()
    monkeypatch.setattr(paths, 'UPLOADS_DIR', uploads)
    app = Flask(__name__)
    app.register_blueprint(browse.browse_bp)
    app.config['TESTING'] = True

    def upstream(name, chunks):
        response = SimpleNamespace(
            status_code=200,
            headers={'Content-Disposition': f'attachment; filename="{name}"'},
            iter_content=lambda _: iter(chunks),
        )
        monkeypatch.setattr(browse.requests, 'get', lambda *a, **kw: response)

    return app.test_client(), uploads, upstream


def test_download_replaces_complete_file(download_env):
    client, uploads, upstream = download_env
    (uploads / 'report.txt').write_text('old')
    upstream('report.txt', [b'new', b' document'])
    response = client.post('/api/browse/download', json={})
    assert response.status_code == 200
    assert response.json == {'saved': 'report.txt', 'url': '/uploads/report.txt'}
    assert (uploads / 'report.txt').read_bytes() == b'new document'
    assert list(uploads.glob('.browse-download-*')) == []


def test_download_rejects_symlink_escape(download_env, tmp_path):
    client, uploads, upstream = download_env
    outside = tmp_path / 'secret.txt'
    outside.write_text('private')
    (uploads / 'report.txt').symlink_to(outside)
    upstream('report.txt', [b'overwritten'])
    assert client.post('/api/browse/download', json={}).status_code == 400
    assert outside.read_text() == 'private'


def test_download_rename_does_not_follow_raced_symlink(download_env, tmp_path):
    client, uploads, upstream = download_env
    outside = tmp_path / 'secret.txt'
    outside.write_text('private')

    def chunks():
        (uploads / 'report.txt').symlink_to(outside)
        yield b'download'

    upstream('report.txt', chunks())
    assert client.post('/api/browse/download', json={}).status_code == 200
    assert outside.read_text() == 'private'
    assert not (uploads / 'report.txt').is_symlink()
    assert (uploads / 'report.txt').read_bytes() == b'download'


def test_interrupted_download_preserves_original(download_env):
    client, uploads, upstream = download_env
    (uploads / 'report.txt').write_text('original')

    def chunks():
        yield b'partial'
        raise requests.ConnectionError('connection interrupted')

    upstream('report.txt', chunks())
    assert client.post('/api/browse/download', json={}).status_code == 503
    assert (uploads / 'report.txt').read_text() == 'original'
    assert list(uploads.glob('.browse-download-*')) == []


@pytest.mark.parametrize('name', ['.', '..', 'nested\\file', 'bad\x00name'])
def test_invalid_download_filename(download_env, name):
    client, uploads, upstream = download_env
    upstream(name, [b'bad'])
    assert client.post('/api/browse/download', json={}).status_code == 400
    assert list(uploads.iterdir()) == []


def test_download_preserves_unicode_basename(download_env):
    client, uploads, upstream = download_env
    upstream('/source/résumé.pdf', [b'pdf'])
    assert client.post('/api/browse/download', json={}).status_code == 200
    assert (uploads / 'résumé.pdf').read_bytes() == b'pdf'
