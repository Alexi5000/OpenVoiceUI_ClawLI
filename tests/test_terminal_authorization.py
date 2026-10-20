"""Exercise the terminal handler without starting a real shell."""
import ast
import json
import logging
import os
import pty
import types
from pathlib import Path
from unittest.mock import Mock

import pytest
from flask import Flask, request


@pytest.fixture
def terminal(monkeypatch, tmp_path):
    source = Path(__file__).parents[1] / "server.py"
    node = next(n for n in ast.parse(source.read_text()).body
                if isinstance(n, ast.FunctionDef) and n.name == "terminal_websocket")
    node.decorator_list = []
    auth = types.ModuleType("services.auth")
    auth.get_token_from_request = lambda: request.cookies.get("__session")
    auth.verify_clerk_token = lambda token: {"admin-token": "admin", "voice-token": "voice"}.get(token)
    auth.is_admin_user = lambda user: user == "admin"
    paths = types.ModuleType("services.paths")
    paths.CODE_WORKSPACE_DIR = tmp_path / "workspace"
    monkeypatch.setitem(__import__("sys").modules, "services.auth", auth)
    monkeypatch.setitem(__import__("sys").modules, "services.paths", paths)
    scope = {"os": os, "json": json, "logger": logging.getLogger(__name__), "request": request}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), "exec"), scope)
    monkeypatch.setenv("AGENT_API_KEY", "internal-test-key")
    return Flask(__name__), scope["terminal_websocket"], paths.CODE_WORKSPACE_DIR


@pytest.mark.parametrize("cookie,key,origin", [
    (None, None, None),
    ("invalid", None, None),
    ("voice-token", None, None),
    ("voice-token", "wrong", None),
    ("admin-token", None, "https://untrusted.example"),
    ("admin-token", None, "null"),
    ("admin-token", None, "http://localhost"),
    ("admin-token", None, "https://localhost/path"),
    ("admin-token", None, "https://localhost?query"),
    ("admin-token", None, "https://localhost#fragment"),
    ("admin-token", None, "https://["),
    (None, "internal-test-key", "https://untrusted.example"),
    (None, "non-ascii-\u2603", None),
])
def test_rejects_before_workspace_or_shell(terminal, monkeypatch, cookie, key, origin):
    app, handler, workspace = terminal
    headers = {}
    if cookie:
        headers["Cookie"] = "__session=" + cookie
    if key is not None:
        headers["X-Agent-Key"] = key
    if origin is not None:
        headers["Origin"] = origin
    fork = Mock(side_effect=AssertionError("must not spawn shell"))
    monkeypatch.setattr(pty, "fork", fork)
    ws = Mock()
    with app.test_request_context("/ws/terminal", base_url="https://localhost", headers=headers):
        handler(ws)
    fork.assert_not_called()
    assert not workspace.exists()
    ws.close.assert_called_once()
    assert json.loads(ws.send.call_args.args[0])["message"] == "Unauthorized"


@pytest.mark.parametrize("cookie,key,origin", [
    ("admin-token", None, "https://localhost"),
    ("admin-token", None, None),
    (None, "internal-test-key", None),
    ("voice-token", "internal-test-key", None),
])
def test_admin_and_privileged_agent_reach_shell_boundary(terminal, monkeypatch, cookie, key, origin):
    app, handler, workspace = terminal
    headers = {}
    if cookie:
        headers["Cookie"] = "__session=" + cookie
    if key:
        headers["X-Agent-Key"] = key
    if origin:
        headers["Origin"] = origin
    class BoundaryReached(Exception):
        pass
    monkeypatch.setattr(pty, "fork", Mock(side_effect=BoundaryReached))
    with app.test_request_context("/ws/terminal", base_url="https://localhost", headers=headers):
        with pytest.raises(BoundaryReached):
            handler(Mock())
    assert workspace.is_dir()


def test_unconfigured_agent_key_denies_empty_header(terminal, monkeypatch):
    app, handler, workspace = terminal
    monkeypatch.delenv("AGENT_API_KEY")
    monkeypatch.setattr(pty, "fork", Mock(side_effect=AssertionError("must not spawn shell")))
    ws = Mock()
    with app.test_request_context("/ws/terminal", headers={"X-Agent-Key": ""}):
        handler(ws)
    assert not workspace.exists()
    ws.close.assert_called_once()
