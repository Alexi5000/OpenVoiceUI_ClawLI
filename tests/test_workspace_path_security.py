import os

import pytest
from flask import Flask

from routes import workspace


@pytest.fixture
def env(tmp_path, monkeypatch):
    ws = tmp_path / 'workspace'
    (ws / 'Agent').mkdir(parents=True)
    (ws / 'Agent' / 'notes.md').write_text('hello')
    (ws / 'Agent' / 'pic.png').write_bytes(b'\x89PNG\r\n\x1a\n')
    uploads = tmp_path / 'uploads'
    uploads.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'secret.md').write_text('secret')
    (outside / 'secret.png').write_bytes(b'\x89PNG\r\n\x1a\n')
    monkeypatch.setattr(workspace, 'WORKSPACE_DIR', ws)
    monkeypatch.setitem(workspace._WRITABLE_MAP, 'Uploads', uploads)
    app = Flask(__name__)
    app.register_blueprint(workspace.workspace_bp)
    return app.test_client(), ws, uploads, outside


def test_authorized_reads(env):
    client, ws, _, _ = env
    assert client.get('/api/workspace/file', query_string={'path': 'Agent/notes.md'}).json['content'] == 'hello'
    assert client.get('/api/workspace/file', query_string={'path': '/Agent/notes.md'}).json['content'] == 'hello'
    assert client.get('/api/workspace/raw', query_string={'path': 'Agent/pic.png'}).status_code == 200
    names = [e['name'] for e in client.get('/api/workspace/browse', query_string={'path': ''}).json['entries']]
    assert names == ['Agent']


@pytest.mark.parametrize('path', ['../outside/secret.md', 'Agent/../../outside/secret.md', 'Agent/notes.md\x00.png'])
def test_traversal_rejected(env, path):
    client, _, _, _ = env
    for route in ('/api/workspace/file', '/api/workspace/raw', '/api/workspace/browse'):
        assert client.get(route, query_string={'path': path}).status_code == 400


def test_symlink_substitution_rejected(env):
    client, ws, _, outside = env
    os.symlink(outside, ws / 'Agent' / 'escape')
    os.symlink(outside / 'secret.png', ws / 'Agent' / 'innocent.png')
    assert client.get('/api/workspace/file', query_string={'path': 'Agent/escape/secret.md'}).status_code == 400
    assert client.get('/api/workspace/raw', query_string={'path': 'Agent/innocent.png'}).status_code == 400


def test_writable_area(env):
    client, _, uploads, outside = env
    r = client.put('/api/workspace/file', query_string={'path': 'Uploads/a/new.txt'}, json={'content': 'x'})
    assert r.status_code == 200 and (uploads / 'a' / 'new.txt').read_text() == 'x'
    r = client.put('/api/workspace/file', query_string={'path': 'Uploads/../outside/pwn.txt'}, json={'content': 'x'})
    assert r.status_code == 403 and not (outside / 'pwn.txt').exists()
    os.symlink(outside, uploads / 'link')
    r = client.put('/api/workspace/file', query_string={'path': 'Uploads/link/pwn.txt'}, json={'content': 'x'})
    assert r.status_code == 403 and not (outside / 'pwn.txt').exists()
    assert client.get('/api/workspace/writable', query_string={'path': 'Uploads'}).json['writable'] is True
    assert client.get('/api/workspace/writable', query_string={'path': 'Readonly/x'}).json['writable'] is False
