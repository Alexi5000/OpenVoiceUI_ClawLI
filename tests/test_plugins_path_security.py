import io
import json
import os
import zipfile

import pytest

from services import plugins


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    pdir = tmp_path / 'plugins'
    cat = tmp_path / 'catalog'
    (cat / 'good').mkdir(parents=True)
    (cat / 'good' / 'plugin.json').write_text(json.dumps({'id': 'good', 'version': '1.0'}))
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'plugin.json').write_text(json.dumps({'id': 'evil'}))
    monkeypatch.setattr(plugins, 'PLUGIN_DIR', pdir)
    monkeypatch.setattr(plugins, 'PLUGIN_CATALOG_DIR', cat)
    monkeypatch.setattr(plugins, '_registry', {})
    monkeypatch.setattr(plugins, '_download_remote_plugin', lambda pid: None)
    return pdir, cat, outside


def test_install_update_uninstall_legitimate(dirs):
    pdir, cat, _ = dirs
    m = plugins.install_plugin('good')
    assert m['id'] == 'good' and (pdir / 'good' / 'plugin.json').is_file()
    r = plugins.update_plugin('good')
    assert r['id'] == 'good' and any(p.name.startswith('good.old-') for p in pdir.iterdir())
    assert plugins.uninstall_plugin('good') is True
    assert not (pdir / 'good').exists()


@pytest.mark.parametrize('pid', ['../outside', '..', '.', '', '/etc', 'a/b', 'a\\b', 'x\x00'])
def test_invalid_plugin_ids_rejected(dirs, pid):
    pdir, cat, outside = dirs
    (pdir).mkdir(exist_ok=True)
    assert plugins.install_plugin(pid) is None
    assert plugins.uninstall_plugin(pid) is False
    assert plugins.update_plugin(pid) is None
    assert outside.exists() and (outside / 'plugin.json').exists()


def test_symlinked_plugin_dir_not_uninstalled(dirs):
    pdir, cat, outside = dirs
    pdir.mkdir()
    os.symlink(outside, pdir / 'linked')
    assert plugins.uninstall_plugin('linked') is False
    assert (outside / 'plugin.json').exists()


def test_symlinked_catalog_entry_not_installed(dirs):
    pdir, cat, outside = dirs
    os.symlink(outside, cat / 'linked')
    assert plugins.install_plugin('linked') is None


def test_lore_traversal_skipped(dirs, tmp_path, monkeypatch):
    pdir, cat, outside = dirs
    (cat / 'lorep').mkdir()
    (cat / 'lorep' / 'lore').mkdir()
    (cat / 'lorep' / 'lore' / 'ok.md').write_text('ok')
    (cat / 'lorep' / 'plugin.json').write_text(json.dumps({
        'id': 'lorep', 'lore': {'files': ['lore/ok.md', '../../outside/plugin.json', '/etc/passwd']}}))
    ws = tmp_path / 'ws'
    ws.mkdir()
    real_path = plugins.Path

    def fake_path(p, *a):
        return real_path(str(ws)) if p == '/app/runtime/workspace/Agent' else real_path(p, *a)
    monkeypatch.setattr(plugins, 'Path', fake_path)
    plugins.install_plugin('lorep')
    assert (ws / 'lorep' / 'ok.md').read_text() == 'ok'
    assert not (ws / 'lorep' / 'outside').exists()
    assert sorted(p.name for p in (ws / 'lorep').rglob('*')) == ['ok.md']


def test_remote_zip_slip_member_skipped(tmp_path, monkeypatch):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        zf.writestr('repo-main/demo/plugin.json', '{"id": "demo"}')
        zf.writestr('repo-main/demo/../../escaped.txt', 'pwn')
        zf.writestr('repo-main/demo/ok/file.txt', 'ok')

    class Resp:
        ok = True
        content = buf.getvalue()

    monkeypatch.setattr(plugins.requests, 'get', lambda *a, **k: Resp())
    out = plugins._download_remote_plugin('demo')
    try:
        assert (out / 'plugin.json').is_file()
        assert (out / 'ok' / 'file.txt').read_text() == 'ok'
        assert not (out.parent / 'escaped.txt').exists()
        assert not (out / '..' / 'escaped.txt').resolve().exists()
    finally:
        import shutil
        shutil.rmtree(out)
