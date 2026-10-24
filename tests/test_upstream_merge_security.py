import os
import stat
import threading

import pytest

from routes import canvas, suno
from services.safe_paths import UnsafePathError


def test_canvas_replace_does_not_follow_predictable_temporary_symlink(tmp_path):
    outside = tmp_path / 'private'
    outside.write_text('unchanged')
    page = tmp_path / 'page.html'
    old_temp = tmp_path / f'.page.html.{os.getpid()}.{threading.get_ident()}.tmp'
    old_temp.symlink_to(outside)
    canvas._write_page_replacing(page, '<p>page</p>')
    assert outside.read_text() == 'unchanged'
    assert page.read_text() == '<p>page</p>'
    assert stat.S_IMODE(page.stat().st_mode) == 0o660


def test_process_download_rejects_symlink_destination(tmp_path, monkeypatch):
    root = tmp_path / 'music'
    root.mkdir()
    target = tmp_path / 'private'
    target.write_bytes(b'unchanged')
    output = root / 'result.wav'
    output.symlink_to(target)
    monkeypatch.setattr(suno, 'GENERATED_MUSIC_DIR', root)
    monkeypatch.setattr(suno, '_is_safe_download_url', lambda url: True)
    monkeypatch.setattr(suno, 'download_public', lambda url, **kwargs: b'untrusted')
    assert not suno._download_capped('https://example.org/result.wav', output)
    assert target.read_bytes() == b'unchanged'


def test_process_download_rejects_blocked_redirect(tmp_path, monkeypatch):
    monkeypatch.setattr(suno, 'GENERATED_MUSIC_DIR', tmp_path)
    monkeypatch.setattr(suno, '_is_safe_download_url', lambda url: True)

    def reject(url, **kwargs):
        raise ValueError('Download host resolves to a non-public address')

    monkeypatch.setattr(suno, 'download_public', reject)
    output = tmp_path / 'result.wav'
    assert not suno._download_capped('https://example.org/redirect', output)
    assert not output.exists()


def test_process_directory_rejects_external_symlink(tmp_path, monkeypatch):
    root = tmp_path / 'music'
    root.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    (root / 'wav').symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(suno, 'GENERATED_MUSIC_DIR', root)
    with pytest.raises(UnsafePathError):
        suno._process_dir('wav_convert')
