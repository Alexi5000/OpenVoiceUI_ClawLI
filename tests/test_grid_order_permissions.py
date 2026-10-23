import os
import stat

import pytest

from routes import grid_gen


def test_order_directory_restricts_other_users_and_preserves_group(tmp_path, monkeypatch):
    orders = tmp_path / 'grid-orders'
    orders.mkdir(mode=0o777)
    group = orders.stat().st_gid
    monkeypatch.setattr(grid_gen, 'ORDERS_DIR', orders)
    assert grid_gen._orders_dir() == orders
    assert stat.S_IMODE(orders.stat().st_mode) == 0o2770
    assert orders.stat().st_gid == group
    (orders / 'status.json').write_text('{}')
    assert (orders / 'status.json').stat().st_gid == group


def test_order_directory_rejects_symlink_without_changing_target(tmp_path, monkeypatch):
    outside = tmp_path / 'outside'
    outside.mkdir(mode=0o700)
    orders = tmp_path / 'grid-orders'
    orders.symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(grid_gen, 'ORDERS_DIR', orders)
    with pytest.raises(OSError):
        grid_gen._orders_dir()
    assert stat.S_IMODE(outside.stat().st_mode) == 0o700


def test_order_directory_permission_failure_is_not_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(grid_gen, 'ORDERS_DIR', tmp_path / 'grid-orders')
    def denied(*args):
        raise PermissionError('denied')
    monkeypatch.setattr(os, 'fchmod', denied)
    with pytest.raises(PermissionError):
        grid_gen._orders_dir()


def test_order_directory_rejects_silently_stripped_setgid(tmp_path, monkeypatch):
    orders = tmp_path / 'grid-orders'
    monkeypatch.setattr(grid_gen, 'ORDERS_DIR', orders)
    real_fchmod = os.fchmod
    def without_setgid(fd, mode):
        real_fchmod(fd, mode & ~stat.S_ISGID)
    monkeypatch.setattr(os, 'fchmod', without_setgid)
    with pytest.raises(PermissionError, match='setgid'):
        grid_gen._orders_dir()
    assert stat.S_IMODE(orders.stat().st_mode) == 0o770
