"""Grid Creator order tracking.

The Grid Creator page records an order here, then triggers this tenant's voice agent
(via a canvas 'speak' shortcut) to mesh-send the job to the Mac creative node under the
agent's own identity — so the Mac knows the client/brand. The Mac generates via ChatGPT
(no per-image cost), writes the finished images into this tenant's uploads/, and drops a
status marker the page polls here.

This route only OWNS the order record + status read-back. It deliberately does NOT touch the
mesh queue (OVU has no mesh mount) — the voice agent is the bridge, per the confirmed contract
in docs/jambot/grid-creator-spec.md.

Order/status files live UNDER the uploads/ dir — the one runtime subdir that is bind-mounted
to the host (`/mnt/clients/<t>/openvoiceui/uploads/`) and uses a shared group, so
BOTH this route (container uid 1001) and the Mac creative node (host uid 1000) can write to it.
A top-level runtime/grid-orders/ would live only inside the container fs — the Mac's host-side
marker would be invisible to the page. Do NOT move this out from under uploads/ without adding a
corresponding compose bind-mount to every tenant.
  uploads/grid-orders/<request_id>.json         # created by this route (status=queued)
  uploads/grid-orders/<request_id>.status.json  # written by the Mac on progress/completion
Host path the Mac writes to: /mnt/clients/<client_id>/openvoiceui/uploads/grid-orders/
"""
from __future__ import annotations

import json
import os
import stat
import time
from pathlib import Path

from flask import Blueprint, request, jsonify

from services.paths import RUNTIME_DIR, UPLOADS_DIR
from services.safe_paths import UnsafePathError, safe_join

grid_gen_bp = Blueprint('grid_gen', __name__)

# Under uploads/ so the Mac's host-side markers are visible here.
ORDERS_DIR = RUNTIME_DIR / 'uploads' / 'grid-orders'
_VALID_TYPES = {'post', 'logo', 'character', 'mascot'}
_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.tiff', '.tif', '.avif', '.heic', '.heif'}
_MAX_REFS = 6


def _sanitize_refs(raw) -> list:
    """Keep only real image files that actually live in this tenant's uploads/ dir.

    Refs are basenames the user picked/uploaded (e.g. 'logo__a1b2c3d4.png'). We reject anything
    with a path separator or that doesn't resolve to an existing image directly under uploads/,
    so a ref can never point the Mac at a file outside the tenant's own uploads.
    """
    out = []
    for r in (raw or [])[:24]:
        name = (str(r) or '').strip().lstrip('/')
        if not name or '/' in name or '\\' in name or '..' in name:
            continue
        try:
            p = safe_join(UPLOADS_DIR, name, allow_base=False)
        except UnsafePathError:
            continue
        if p.suffix.lower() in _IMAGE_EXTS and p.is_file():
            if name not in out:
                out.append(name)
        if len(out) >= _MAX_REFS:
            break
    return out


def _orders_dir() -> Path:
    ORDERS_DIR.mkdir(mode=0o770, parents=True, exist_ok=True)
    before = ORDERS_DIR.lstat()
    if not stat.S_ISDIR(before.st_mode):
        raise OSError('order storage must be a directory')
    fd = os.open(ORDERS_DIR, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        opened = os.fstat(fd)
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise OSError('order storage changed during access')
        os.fchmod(fd, 0o2770)
        if stat.S_IMODE(os.fstat(fd).st_mode) != 0o2770:
            raise PermissionError("order storage requires setgid shared-group permissions")
    finally:
        os.close(fd)
    return ORDERS_DIR


@grid_gen_bp.route('/api/grid-gen/orders', methods=['POST'])
def create_order():
    d = request.get_json(silent=True) or {}
    rid = (d.get('request_id') or '').strip()
    if not rid or '/' in rid or '..' in rid:
        return jsonify({'error': 'valid request_id required'}), 400
    if (d.get('grid_type') or '') not in _VALID_TYPES:
        return jsonify({'error': 'invalid grid_type'}), 400
    order = {
        'request_id': rid,
        'grid_type': d.get('grid_type'),
        'brief': (d.get('brief') or '')[:2000],
        'count': max(1, min(24, int(d.get('count') or 9))),
        'aspect': d.get('aspect') or '1:1',
        'layout': 'composite' if d.get('layout') != 'separate' else 'separate',
        # Reference images the user uploaded/picked from uploads/. The Mac reads these from this
        # order record (authoritative) and passes them to the generator as --img inputs — the
        # agent path never has to relay filenames. Basenames only; validated to exist in uploads/.
        'refs': _sanitize_refs(d.get('refs')),
        'status': 'queued',
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }
    try:
        order_path = safe_join(_orders_dir(), f'{rid}.json', allow_base=False)
    except UnsafePathError:
        return jsonify({'error': 'valid request_id required'}), 400
    order_path.write_text(json.dumps(order))
    return jsonify({'ok': True, 'request_id': rid, 'refs': order['refs']})


@grid_gen_bp.route('/api/grid-gen/uploads', methods=['GET'])
def list_uploads():
    """Image files in this tenant's uploads/ dir, for the reference-image picker.

    Flat listing (excludes subdirs like grid-orders/, albums/) newest-first, images only.
    """
    out = []
    try:
        entries = [p for p in UPLOADS_DIR.iterdir()
                   if p.is_file() and not p.name.startswith('.') and p.suffix.lower() in _IMAGE_EXTS]
    except OSError:
        entries = []
    for p in sorted(entries, key=lambda p: p.stat().st_mtime, reverse=True)[:300]:
        out.append({'name': p.name, 'url': f'/uploads/{p.name}', 'mtime': int(p.stat().st_mtime)})
    return jsonify(out)


@grid_gen_bp.route('/api/grid-gen/orders', methods=['GET'])
def list_orders():
    out = []
    d = _orders_dir()
    for f in sorted(d.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.name.endswith('.status.json'):
            continue
        try:
            order = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        # Merge the Mac's status marker if present (it wins on status/files/error).
        marker = d / f"{order.get('request_id')}.status.json"
        if marker.exists():
            try:
                st = json.loads(marker.read_text())
                for k in ('status', 'files', 'error', 'done', 'updated_at'):
                    if k in st:
                        order[k] = st[k]
            except (OSError, json.JSONDecodeError):
                pass
        out.append(order)
    return jsonify(out[:50])
