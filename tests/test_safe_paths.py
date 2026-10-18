import os

import pytest

from services.safe_paths import UnsafePathError, is_within, safe_filename, safe_join


@pytest.fixture
def base(tmp_path):
    root = tmp_path / 'base'
    (root / 'sub').mkdir(parents=True)
    (root / 'sub' / 'file.txt').write_text('ok')
    return root


def test_joins_legitimate_relative_paths(base):
    assert safe_join(base, 'sub', 'file.txt') == (base / 'sub' / 'file.txt').resolve()
    assert safe_join(base, 'sub/file.txt') == (base / 'sub' / 'file.txt').resolve()
    assert safe_join(str(base), 'new-file.json') == (base / 'new-file.json').resolve()
    assert safe_join(base, './sub') == (base / 'sub').resolve()


def test_base_itself(base):
    assert safe_join(base) == base.resolve()
    assert safe_join(base, '') == base.resolve()
    with pytest.raises(UnsafePathError):
        safe_join(base, '', allow_base=False)
    with pytest.raises(UnsafePathError):
        safe_join(base, '.', allow_base=False)


@pytest.mark.parametrize('part', [
    '..', '../etc/passwd', 'sub/../../x', 'sub/..', '..\\x', 'sub\\..\\..\\x',
])
def test_rejects_traversal(base, part):
    with pytest.raises(UnsafePathError):
        safe_join(base, part)


@pytest.mark.parametrize('part', ['/etc/passwd', '\\windows\\system32', 'C:\\x', 'c:x', '//server/share'])
def test_rejects_absolute_paths(base, part):
    with pytest.raises(UnsafePathError):
        safe_join(base, part)


def test_rejects_nul(base):
    with pytest.raises(UnsafePathError):
        safe_join(base, 'file\x00.txt')


def test_rejects_absolute_in_later_part(base):
    with pytest.raises(UnsafePathError):
        safe_join(base, 'sub', '/etc/passwd')


def test_rejects_symlink_escape(base, tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'secret').write_text('secret')
    os.symlink(outside, base / 'link')
    with pytest.raises(UnsafePathError):
        safe_join(base, 'link', 'secret')
    with pytest.raises(UnsafePathError):
        safe_join(base, 'link')
    os.symlink(outside / 'secret', base / 'filelink')
    with pytest.raises(UnsafePathError):
        safe_join(base, 'filelink')


def test_allows_symlink_inside_base(base):
    os.symlink(base / 'sub', base / 'alias')
    assert safe_join(base, 'alias', 'file.txt') == (base / 'sub' / 'file.txt').resolve()


def test_symlinked_base_is_resolved(base, tmp_path):
    link_base = tmp_path / 'link-base'
    os.symlink(base, link_base)
    assert safe_join(link_base, 'sub', 'file.txt') == (base / 'sub' / 'file.txt').resolve()


def test_sibling_prefix_is_not_inside(base, tmp_path):
    sibling = tmp_path / 'base-evil'
    sibling.mkdir()
    os.symlink(sibling, base / 'sib')
    with pytest.raises(UnsafePathError):
        safe_join(base, 'sib')
    assert not is_within(base, sibling)
    assert is_within(base, base / 'sub' / 'file.txt')
    assert is_within(base, base)


@pytest.mark.parametrize('name', ['file.txt', 'My File-1.png', 'a'])
def test_safe_filename_accepts(name):
    assert safe_filename(name) == name


@pytest.mark.parametrize('name', ['', '.', '..', '.hidden', 'a/b', 'a\\b', 'x\x00', '-rf'])
def test_safe_filename_rejects(name):
    with pytest.raises(UnsafePathError):
        safe_filename(name)
