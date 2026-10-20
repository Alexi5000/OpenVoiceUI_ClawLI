import ast
import asyncio
import logging
import os
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import uuid

import pytest


@pytest.fixture
def capture(tmp_path):
    source = Path(__file__).resolve().parents[1] / "deploy/browse-service/server.py"
    tree = ast.parse(source.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "BrowseService")
    method = next(n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "_save_download")
    namespace = dict(os=os, shutil=shutil, tempfile=tempfile, uuid=uuid,
                     time=SimpleNamespace(time=lambda: 123), logger=logging.getLogger(__name__),
                     _downloads_dir=lambda tenant: tmp_path)
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), "exec"), namespace)
    session = SimpleNamespace(tenant="example", last_download=None)

    async def save(path):
        Path(path).write_bytes(b"complete download")

    download = SimpleNamespace(suggested_filename="report.txt", save_as=save)
    return namespace, session, download


def test_complete_download_and_shared_mode(capture, tmp_path):
    namespace, session, download = capture
    asyncio.run(namespace["_save_download"](None, session, download))
    result = tmp_path / session.last_download
    assert result.read_bytes() == b"complete download"
    assert result.stat().st_mode & 0o777 == 0o664


def test_old_predictable_symlink_cannot_overwrite(capture, tmp_path):
    namespace, session, download = capture
    outside = tmp_path.parent / "private.txt"
    outside.write_text("private")
    outside.chmod(0o600)
    (tmp_path / "browse-123-report.txt").symlink_to(outside)
    asyncio.run(namespace["_save_download"](None, session, download))
    assert outside.read_text() == "private"
    assert outside.stat().st_mode & 0o777 == 0o600
    assert session.last_download != "browse-123-report.txt"


@pytest.mark.parametrize("symlink", [False, True])
def test_collision_never_overwrites(capture, tmp_path, symlink):
    namespace, session, download = capture
    namespace["uuid"] = SimpleNamespace(uuid4=lambda: SimpleNamespace(hex="fixed"))
    dest = tmp_path / "browse-fixed-report.txt"
    original = tmp_path / "original"
    original.write_text("keep")
    if symlink:
        dest.symlink_to(original)
    else:
        dest.write_text("keep")
    asyncio.run(namespace["_save_download"](None, session, download))
    assert dest.read_text() == "keep"
    assert original.read_text() == "keep"
    assert session.last_download is None


def test_failed_transfer_publishes_nothing(capture, tmp_path):
    namespace, session, download = capture

    async def fail(path):
        Path(path).write_bytes(b"partial")
        raise OSError("interrupted")

    download.save_as = fail
    asyncio.run(namespace["_save_download"](None, session, download))
    assert list(tmp_path.iterdir()) == []
    assert session.last_download is None
