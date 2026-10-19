import pytest
from flask import Flask

from routes import conversation, vision, custom_faces
from services import canvas_versioning, vault
from services.safe_paths import UnsafePathError


def test_chat_image_requires_actual_upload_root(tmp_path, monkeypatch):
    uploads = tmp_path / 'runtime' / 'uploads'
    uploads.mkdir(parents=True)
    workspace = tmp_path / 'workspace'
    monkeypatch.setattr(conversation, '_UPLOADS_DIR', uploads)
    monkeypatch.setattr(conversation, '_WORKSPACE_DIR', workspace)
    good = uploads / 'photo.png'
    good.write_bytes(b'photo')
    outside = tmp_path / 'other' / 'uploads'
    outside.mkdir(parents=True)
    secret = outside / 'private.png'
    secret.write_bytes(b'secret')
    (uploads / 'escape.png').symlink_to(secret)
    assert conversation._resolve_upload_image(str(secret)) is None
    assert conversation._resolve_upload_image('escape.png') is None
    assert conversation._resolve_upload_image('../private.png') is None
    assert conversation._resolve_upload_image(str(good)) == good
    assert conversation._resolve_upload_image('uploads/photo.png') == good


def test_empty_face_name_cannot_delete_all_faces(tmp_path, monkeypatch):
    root = tmp_path / 'faces'
    root.mkdir()
    (root / 'keep.jpg').write_bytes(b'keep')
    monkeypatch.setattr(vision, 'FACES_DIR', root)
    app = Flask(__name__)
    app.register_blueprint(vision.vision_bp)
    response = app.test_client().delete('/api/faces/!!!')
    assert response.status_code == 404
    assert (root / 'keep.jpg').read_bytes() == b'keep'


def test_promote_blocks_external_canvas(tmp_path, monkeypatch):
    canvas = tmp_path / 'canvas'
    canvas.mkdir()
    monkeypatch.setattr(custom_faces, 'CANVAS_PAGES_DIR', canvas)
    app = Flask(__name__)
    app.register_blueprint(custom_faces.custom_faces_bp)
    response = app.test_client().post('/api/custom-faces/promote', json={
        'canvas_page_id': '../secret', 'force': True,
    })
    assert response.status_code == 400


def test_version_read_and_restore_cannot_escape(tmp_path, monkeypatch):
    monkeypatch.setattr(canvas_versioning, 'CANVAS_PAGES_DIR', tmp_path / 'canvas')
    assert canvas_versioning.get_version_content('../secret', 123) is None
    assert not canvas_versioning.restore_version('../secret', 123)


def test_vault_rejects_cross_client_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(vault, '_RUNTIME_VAULT_DIR', tmp_path / 'absent')
    monkeypatch.setattr(vault, '_CLIENTS_DIR', tmp_path / 'clients')
    with pytest.raises(UnsafePathError):
        vault._vault_dir('../other')
    with pytest.raises(UnsafePathError):
        vault._vault_oauth_path('alice', '../../bob/credentials')
    assert vault._vault_oauth_path('alice', 'github') == tmp_path / 'clients/alice/vault/oauth/github.json'
