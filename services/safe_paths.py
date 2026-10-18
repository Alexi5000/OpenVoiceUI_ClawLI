"""Shared filesystem containment helpers.

Every file access whose path is influenced by a request (route parameter,
query string, JSON body, uploaded filename, stored metadata) must be built
with :func:`safe_join` so the resulting path is guaranteed to stay inside a
server-chosen base directory.

``safe_join`` rejects, before touching the filesystem:

* NUL bytes,
* absolute paths (POSIX ``/x``, Windows ``\\x`` / ``C:\\x``),
* ``..`` path segments (with either separator),

and after resolving the candidate with :func:`os.path.realpath` (which follows
symlinks) it requires the result to remain under the resolved base, so a
symlink planted inside the base that points elsewhere is also rejected.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Union

PathPart = Union[str, "os.PathLike[str]"]

_DRIVE_RE = re.compile(r"^[A-Za-z]:")


class UnsafePathError(ValueError):
    """Raised when a requested path would escape its base directory."""


def _check_part(part: PathPart) -> str:
    text = os.fspath(part)
    if not isinstance(text, str):
        raise UnsafePathError("path component must be text")
    if "\x00" in text:
        raise UnsafePathError("NUL byte in path")
    if text.startswith(("/", "\\")) or _DRIVE_RE.match(text) or os.path.isabs(text):
        raise UnsafePathError("absolute path not allowed")
    if any(segment == ".." for segment in re.split(r"[\\/]", text)):
        raise UnsafePathError("parent directory segment not allowed")
    return text


def safe_join(base: PathPart, *parts: PathPart, allow_base: bool = True) -> Path:
    """Join ``parts`` onto ``base`` and return a resolved path inside ``base``.

    ``base`` is trusted (server-chosen); ``parts`` may be user-controlled.
    Raises :class:`UnsafePathError` when the result would leave ``base``
    (traversal, absolute path, NUL byte, or symlink escape). When
    ``allow_base`` is false, a result equal to ``base`` itself is rejected too
    (useful for destructive operations such as delete/rename).
    """
    base_real = os.path.realpath(os.fspath(base))
    checked = [_check_part(part) for part in parts]
    candidate = os.path.realpath(os.path.join(base_real, *checked))
    if candidate == base_real:
        if not allow_base:
            raise UnsafePathError("path resolves to the base directory")
        return Path(base_real)
    prefix = base_real if base_real.endswith(os.sep) else base_real + os.sep
    if not candidate.startswith(prefix):
        raise UnsafePathError("path escapes base directory")
    return Path(candidate)


def is_within(base: PathPart, path: PathPart) -> bool:
    """Return True when ``path`` (after resolving symlinks) is inside ``base``."""
    base_real = os.path.realpath(os.fspath(base))
    candidate = os.path.realpath(os.fspath(path))
    if candidate == base_real:
        return True
    prefix = base_real if base_real.endswith(os.sep) else base_real + os.sep
    return candidate.startswith(prefix)


_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,254}$")


def safe_filename(name: str, pattern: "re.Pattern[str]" = _SAFE_NAME_RE) -> str:
    """Validate a single path component against an allowlist pattern."""
    if not isinstance(name, str) or not pattern.fullmatch(name) or name in {".", ".."}:
        raise UnsafePathError("invalid file name")
    return name
