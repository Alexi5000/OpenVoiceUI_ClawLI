"""Credential synchronization must not expose values or follow writable aliases."""

import errno
import os
import stat

import pytest

from services import vault


def test_private_atomic_update_preserves_unrelated_content(tmp_path):
    path = tmp_path / '.env'
    path.write_text('# retained\nOLD=one\nTOKEN=old\n')
    path.chmod(0o644)
    assert vault._update_env_file(path, {'TOKEN': 'new', 'EXTRA': 'two'})
    assert path.read_text() == '# retained\nOLD=one\nTOKEN=new\n\nEXTRA=two\n'
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert list(tmp_path.iterdir()) == [path]
    assert not vault._update_env_file(path, {'TOKEN': 'new'})


def test_predictable_temp_symlink_cannot_overwrite_another_file(tmp_path):
    path = tmp_path / '.env'
    outside = tmp_path / 'outside'
    outside.write_text('untouched')
    legacy_tmp = path.with_suffix(path.suffix + '.vault-tmp')
    legacy_tmp.symlink_to(outside)
    assert vault._update_env_file(path, {'TOKEN': 'new'})
    assert outside.read_text() == 'untouched'
    assert legacy_tmp.is_symlink()
    assert path.read_text() == 'TOKEN=new\n'


def test_atomic_destination_symlink_is_replaced_without_changing_target(tmp_path):
    outside = tmp_path / 'outside'
    outside.write_text('TOKEN=old\n')
    path = tmp_path / '.env'
    path.symlink_to(outside)
    assert vault._update_env_file(path, {'TOKEN': 'new'})
    assert not path.is_symlink()
    assert outside.read_text() == 'TOKEN=old\n'


def deny_replace(monkeypatch, error=errno.EBUSY):
    def fail(*args):
        raise OSError(error, 'private-value-must-not-appear')
    monkeypatch.setattr(vault.os, 'replace', fail)


@pytest.mark.skipif(not hasattr(os, 'O_NOFOLLOW'), reason='POSIX descriptor fallback')
def test_bind_mount_fallback_preserves_inode_and_makes_file_private(tmp_path, monkeypatch, caplog):
    path = tmp_path / '.env'
    path.write_text('TOKEN=long-old-value\n')
    path.chmod(0o644)
    inode = path.stat().st_ino
    deny_replace(monkeypatch)
    assert vault._update_env_file(path, {'TOKEN': 'new'})
    assert path.stat().st_ino == inode
    assert path.read_text() == 'TOKEN=new\n'
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert list(tmp_path.iterdir()) == [path]
    assert 'private-value-must-not-appear' not in caplog.text


@pytest.mark.parametrize('alias', ['symlink', 'hardlink'])
def test_direct_fallback_refuses_aliases(tmp_path, monkeypatch, alias):
    outside = tmp_path / 'outside'
    outside.write_text('TOKEN=old\n')
    path = tmp_path / '.env'
    if alias == 'symlink':
        path.symlink_to(outside)
    else:
        os.link(outside, path)
    deny_replace(monkeypatch)
    assert not vault._update_env_file(path, {'TOKEN': 'new'})
    assert outside.read_text() == 'TOKEN=old\n'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['.env', 'outside']


def test_unexpected_replace_failure_preserves_existing_file(tmp_path, monkeypatch, caplog):
    path = tmp_path / '.env'
    path.write_text('TOKEN=old\n')
    deny_replace(monkeypatch, errno.EIO)
    assert not vault._update_env_file(path, {'TOKEN': 'new'})
    assert path.read_text() == 'TOKEN=old\n'
    assert list(tmp_path.iterdir()) == [path]
    assert 'private-value-must-not-appear' not in caplog.text


@pytest.mark.skipif(not hasattr(os, 'mkfifo'), reason='POSIX FIFO')
def test_direct_fallback_refuses_fifo_without_blocking(tmp_path, monkeypatch):
    path = tmp_path / '.env'
    os.mkfifo(path)
    deny_replace(monkeypatch)
    assert not vault._update_env_file(path, {'TOKEN': 'new'})
    assert stat.S_ISFIFO(path.stat().st_mode)
