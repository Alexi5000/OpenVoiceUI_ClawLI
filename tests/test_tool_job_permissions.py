import os
import stat
import subprocess
import tempfile

import pytest
from pathlib import Path

from services import tool_jobs


def test_job_mode_remains_shared(tmp_path, monkeypatch):
    monkeypatch.setattr(tool_jobs, 'JOBS_DIR', tmp_path)
    target = tmp_path / 'job.json'
    tool_jobs._write_atomic(target, {'status': 'queued'})
    assert target.stat().st_mode & 0o777 == 0o660
    assert 'queued' in target.read_text()


def test_job_permission_update_cannot_follow_replaced_temporary_path(tmp_path, monkeypatch):
    spool = tmp_path / 'spool'
    spool.mkdir()
    spool.chmod(0o777)
    monkeypatch.setattr(tool_jobs, 'JOBS_DIR', spool)
    private = tmp_path / 'private'
    private.write_text('secret')
    private.chmod(0o600)
    real_chmod = os.chmod

    def swap_before_chmod(path, mode, *args, **kwargs):
        path = Path(path)
        if path.name.startswith('.tmp-'):
            path.unlink()
            path.symlink_to(private)
        return real_chmod(path, mode, *args, **kwargs)

    monkeypatch.setattr(tool_jobs.os, 'chmod', swap_before_chmod)
    tool_jobs._write_atomic(spool / 'job.json', {'status': 'queued'})
    assert private.stat().st_mode & 0o777 == 0o600
    assert private.read_text() == 'secret'


def test_job_directory_preserves_group_and_inherits_it(tmp_path, monkeypatch):
    spool = tmp_path / 'spool'
    spool.mkdir()
    spool.chmod(0o777)
    group = spool.stat().st_gid
    monkeypatch.setattr(tool_jobs, 'JOBS_DIR', spool)
    target = spool / 'job.json'
    tool_jobs._write_atomic(target, {'status': 'queued'})
    assert stat.S_IMODE(spool.stat().st_mode) == 0o2770
    assert spool.stat().st_gid == group
    assert target.stat().st_gid == group
    assert stat.S_IMODE(target.stat().st_mode) == 0o660


def test_job_directory_rejects_symlink(tmp_path, monkeypatch):
    outside = tmp_path / 'outside'
    outside.mkdir(mode=0o700)
    spool = tmp_path / 'spool'
    spool.symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(tool_jobs, 'JOBS_DIR', spool)
    with pytest.raises(OSError):
        tool_jobs._ensure_dir()
    assert stat.S_IMODE(outside.stat().st_mode) == 0o700
    assert not list(outside.iterdir())


def test_job_directory_permission_failure_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(tool_jobs, 'JOBS_DIR', tmp_path / 'spool')
    def denied(*args):
        raise PermissionError('denied')
    monkeypatch.setattr(tool_jobs.os, 'fchmod', denied)
    with pytest.raises(PermissionError):
        tool_jobs._ensure_dir()
    assert not (tmp_path / 'spool' / 'job.json').exists()


@pytest.mark.skipif(os.geteuid() != 0, reason='requires disposable process identity changes')
def test_distinct_worker_uid_can_update_but_outsider_is_denied(monkeypatch):
    with tempfile.TemporaryDirectory(prefix='tool-job-permissions-') as temporary:
        root = Path(temporary)
        root.chmod(0o755)
        spool = root / 'spool'
        spool.mkdir()
        os.chown(spool, os.geteuid(), 23001)
        monkeypatch.setattr(tool_jobs, 'JOBS_DIR', spool)
        target = spool / 'job.json'
        tool_jobs._write_atomic(target, {'status': 'queued'})
        script = """
import json, os, pathlib, sys
os.setgroups([int(sys.argv[2])])
os.setgid(int(sys.argv[2]))
os.setuid(23002)
p = pathlib.Path(sys.argv[1])
assert json.loads(p.read_text())['status'] == 'queued'
p.write_text('{"status":"done"}')
(p.parent / 'worker-status.json').write_text('{}')
"""
        worker = subprocess.run(['/usr/bin/python3', '-c', script, str(target), '23001'], capture_output=True, text=True)
        assert worker.returncode == 0, worker.stderr
        assert 'done' in target.read_text()
        assert (spool / 'worker-status.json').stat().st_gid == 23001
        target.write_text('{"status":"queued"}')
        outsider = subprocess.run(['/usr/bin/python3', '-c', script, str(target), '23003'], capture_output=True, text=True)
        assert outsider.returncode != 0
        assert 'PermissionError' in outsider.stderr
        assert 'queued' in target.read_text()
