import os
from pathlib import Path

from services import tool_jobs


def test_job_mode_remains_shared(tmp_path, monkeypatch):
    monkeypatch.setattr(tool_jobs, 'JOBS_DIR', tmp_path)
    target = tmp_path / 'job.json'
    tool_jobs._write_atomic(target, {'status': 'queued'})
    assert target.stat().st_mode & 0o777 == 0o666
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
