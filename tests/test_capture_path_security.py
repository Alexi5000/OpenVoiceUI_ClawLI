import io
import json
import os

import pytest
from flask import Flask
from PIL import Image

from routes import capture


@pytest.fixture
def env(tmp_path, monkeypatch):
    captures = tmp_path / 'captures'
    albums = captures / 'albums'
    receipts = captures / 'queue-receipts'
    monkeypatch.setattr(capture, 'CAPTURES_DIR', captures)
    monkeypatch.setattr(capture, 'ALBUMS_SUBDIR', albums)
    monkeypatch.setattr(capture, 'RECEIPTS_DIR', receipts)
    monkeypatch.setattr(capture, 'INDEX_PATH', captures / 'index.json')
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'album.json').write_text(json.dumps({'id': 'x', 'secret': True}))
    app = Flask(__name__)
    app.register_blueprint(capture.capture_bp, url_prefix='/api/capture')
    return app.test_client(), albums, receipts, outside


def _jpeg():
    buf = io.BytesIO()
    Image.new('RGB', (8, 8), 'red').save(buf, 'JPEG')
    buf.seek(0)
    return buf


def test_legitimate_album_flow(env):
    client, albums, receipts, _ = env
    album = client.post('/api/capture/albums', json={'name': 'Job'}).json
    aid = album['id']
    assert client.get(f'/api/capture/albums/{aid}').json['name'] == 'Job'
    r = client.post(f'/api/capture/albums/{aid}/photos',
                    data={'file': (_jpeg(), 'p.jpg'), 'client_uuid': 'abc-123'},
                    content_type='multipart/form-data')
    assert r.status_code == 201
    pid = r.json['id']
    assert (receipts / 'abc-123.json').exists()
    assert client.get(f'/api/capture/albums/{aid}/media/{pid}').status_code == 200
    assert client.get(f'/api/capture/albums/{aid}/thumb/{pid}').status_code == 200
    # idempotent replay
    r2 = client.post(f'/api/capture/albums/{aid}/photos',
                     data={'file': (_jpeg(), 'p.jpg'), 'client_uuid': 'abc-123'},
                     content_type='multipart/form-data')
    assert r2.status_code == 200 and r2.json['photo_id'] == pid
    assert client.get('/api/capture/search', query_string={'q': 'job'}).json['total_albums'] == 1


@pytest.mark.parametrize('album_id', ['..', '.'])
def test_album_id_traversal_rejected(env, album_id):
    client, albums, _, outside = env
    # '..' would resolve to captures/album.json (outside the albums dir)
    (albums.parent).mkdir(parents=True, exist_ok=True)
    (albums.parent / 'album.json').write_text('{"leak": 1}')
    for method, url in [('get', f'/api/capture/albums/{album_id}'),
                        ('patch', f'/api/capture/albums/{album_id}'),
                        ('get', f'/api/capture/albums/{album_id}/thumb/x')]:
        r = getattr(client, method)(url, json={})
        assert r.status_code in (400, 404)
        assert b'leak' not in r.data


def test_symlinked_album_escape_rejected(env):
    client, albums, _, outside = env
    albums.mkdir(parents=True)
    os.symlink(outside, albums / 'evil')
    r = client.get('/api/capture/albums/evil')
    assert r.status_code == 400
    assert b'secret' not in r.data


def test_receipt_traversal_rejected(env):
    client, albums, receipts, outside = env
    aid = client.post('/api/capture/albums', json={'name': 'Job'}).json['id']
    (outside / 'r.json').write_text('{"photo_id": "stolen"}')
    r = client.post(f'/api/capture/albums/{aid}/photos',
                    data={'file': (_jpeg(), 'p.jpg'), 'client_uuid': '../../outside/r'},
                    content_type='multipart/form-data')
    assert r.status_code == 400
    assert b'stolen' not in r.data
    r = client.post(f'/api/capture/albums/{aid}/photos',
                    data={'file': (_jpeg(), 'p.jpg'), 'client_uuid': '/etc/passwd'},
                    content_type='multipart/form-data')
    assert r.status_code == 400


def test_index_entry_with_traversal_id_is_skipped(env):
    client, albums, _, outside = env
    albums.mkdir(parents=True)
    capture.INDEX_PATH.write_text(json.dumps([{'id': '../../outside', 'name': 'zzz'}]))
    r = client.get('/api/capture/search', query_string={'q': 'zzz'})
    assert r.status_code == 200 and r.json['total_albums'] == 0
    r = client.get('/api/capture/albums/nearby', query_string={'lat': 1, 'lng': 1})
    assert r.status_code == 200 and r.json == []
