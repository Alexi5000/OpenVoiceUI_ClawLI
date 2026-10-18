import ast
import logging
import os
from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest
import requests
from flask import Flask, jsonify, request
from routes import fal


@pytest.mark.parametrize('model', sorted(fal.FAL_MODELS))
def test_fal_only_uses_known_provider_endpoints(model, monkeypatch):
    monkeypatch.setattr(fal, 'FAL_KEY', 'test-placeholder')
    app = Flask(__name__)
    app.register_blueprint(fal.fal_bp)
    with patch.object(fal.http, 'post') as post:
        post.return_value.status_code = 200
        post.return_value.json.return_value = {'images': []}
        response = app.test_client().post('/api/fal/image', json={'prompt': 'image', 'model': model})
        assert response.status_code == 200
        assert post.call_args.args[0] == 'https://fal.run/' + model
        assert post.call_args.kwargs['allow_redirects'] is False


@pytest.mark.parametrize('model', ['../admin', 'fal-ai/flux/dev?secret=1', '//localhost/admin', ['fal-ai/flux/dev']])
def test_fal_rejects_unknown_or_nonstring_models(model, monkeypatch):
    monkeypatch.setattr(fal, 'FAL_KEY', 'test-placeholder')
    app = Flask(__name__)
    app.register_blueprint(fal.fal_bp)
    with patch.object(fal.http, 'post') as post:
        assert app.test_client().post('/api/fal/image', json={'prompt': 'image', 'model': model}).status_code == 400
        post.assert_not_called()


def test_search_keeps_query_separate_from_destination_and_preserves_proxy(monkeypatch):
    source = Path('server.py').read_text()
    function = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == 'web_search')
    function.decorator_list = []
    module = ast.Module(body=[function], type_ignores=[])
    namespace = {'request': request, 'jsonify': jsonify, 'requests': requests, 'os': os, 'logger': logging.getLogger(__name__)}
    exec(compile(module, 'server.py', 'exec'), namespace)
    app = Flask(__name__)
    app.add_url_rule('/api/search', view_func=namespace['web_search'], methods=['POST'])
    query = 'query&redirect=http://127.0.0.1/#fragment'
    monkeypatch.setenv('BROWSE_PROXY_SERVER', 'socks5h://configured-proxy:1080')
    with patch.object(requests, 'get') as get:
        get.return_value.text = ''
        assert app.test_client().post('/api/search', json={'query': query}).status_code == 200
        assert get.call_args.args[0] == 'https://html.duckduckgo.com/html/'
        assert get.call_args.kwargs['params'] == {'q': query}
        assert get.call_args.kwargs['proxies']['https'] == 'socks5h://configured-proxy:1080'


@pytest.mark.parametrize('method_name', ['movePageToCategory', 'deletePage', 'toggleStar'])
def test_canvas_mutations_encode_page_id_as_one_segment(method_name):
    source = Path('src/app.js').read_text()
    method = source.split(f'            async {method_name}(', 1)[1].split('\n            },', 1)[0]
    script = '''
const assert = require('node:assert/strict');
const CONFIG = {serverUrl: 'https://configured.example'};
const calls = [];
const fetch = async (...args) => {calls.push(args); return {ok: true};};
const document = {querySelector: () => null};
const methods = {async ''' + method_name + '(' + method + '''}};
(async () => {
 const pageId = '../../admin?x=1#fragment';
 const instance = {...methods, manifest: {pages: {[pageId]: {}}, categories: {}, uncategorized: []}, render() {}, setupDragDrop() {}, async loadManifest() {}};
 await instance[Object.keys(methods)[0]](pageId, 'new');
 assert.equal(calls[0][0], 'https://configured.example/api/canvas/manifest/page/' + encodeURIComponent(pageId));
 for (const invalid of ['', '.', '..', null, {}]) await instance[Object.keys(methods)[0]](invalid, 'new');
 assert.equal(calls.length, 1);
 instance.manifest.pages['normal-page'] = {};
 await instance[Object.keys(methods)[0]]('normal-page', 'new');
 assert.equal(calls[1][0], 'https://configured.example/api/canvas/manifest/page/normal-page');
})().catch(error => {console.error(error); process.exit(1);});
'''
    subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)
