import json
import os
from pathlib import Path
import stat

import pytest

from services import vault


def test_json_update_retains_private_mode_and_payload(tmp_path):
    path = tmp_path / 'credentials.json'
    path.write_text('{}')
    path.chmod(0o600)
    previous = os.umask(0)
    try:
        vault._write_json(path, {'token': 'synthetic-private-marker'})
    finally:
        os.umask(previous)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert json.loads(path.read_text()) == {'token': 'synthetic-private-marker'}
    assert list(tmp_path.iterdir()) == [path]


def test_predictable_temporary_and_destination_symlinks_are_not_followed(tmp_path):
    victim = tmp_path / 'victim'
    victim.write_text('keep')
    path = tmp_path / 'credentials.json'
    path.with_suffix('.tmp').symlink_to(victim)
    path.symlink_to(victim)
    vault._write_json(path, {'token': 'synthetic-private-marker'})
    assert victim.read_text() == 'keep'
    assert not path.is_symlink()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_failed_serialization_preserves_existing_and_cleans_temporary(tmp_path):
    path = tmp_path / 'credentials.json'
    path.write_text('keep')
    with pytest.raises(TypeError):
        vault._write_json(path, {'invalid': object()})
    assert path.read_text() == 'keep'
    assert list(tmp_path.iterdir()) == [path]


def test_environment_read_failure_does_not_log_path_or_exception(tmp_path, monkeypatch, caplog):
    path = tmp_path / 'private-path-marker'
    path.write_text('TOKEN=old')
    def fail(*args, **kwargs):
        raise OSError('synthetic-private-marker')
    monkeypatch.setattr(Path, 'read_text', fail)
    monkeypatch.setattr(vault, '_PLATFORM_OAUTH_ENV', path)
    vault._load_platform_oauth_env()
    assert not vault._update_env_file(path, {'TOKEN': 'new'})
    assert 'synthetic-private-marker' not in caplog.text
    assert 'private-path-marker' not in caplog.text
    assert 'Cannot read' in caplog.text


def test_missing_environment_directory_does_not_log_path(tmp_path, caplog):
    path = tmp_path / 'private-path-marker' / 'config'
    assert not vault._update_env_file(path, {'TOKEN': 'new'})
    assert 'private-path-marker' not in caplog.text
