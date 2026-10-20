import os
from pathlib import Path
import sys
from threading import Thread
from unittest.mock import Mock, patch
from urllib.parse import urlparse

import requests
from flask import Response
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app import create_app
from routes import canvas

source = (ROOT / 'src/app.js').read_text()
push = source.split('async _pushAuthTokenToCanvas() {', 1)[1].split('async _syncSessionCookie()', 1)[0].strip().rstrip(',')
push = 'async _pushAuthTokenToCanvas() {' + push
sync = source.split('async _syncSessionCookie() {', 1)[1].split('renderUserMenu()', 1)[0].strip().rstrip(',')
sync = 'async _syncSessionCookie() {' + sync

preview = '''<!doctype html><h1 id="module">Waiting</h1><script>
window.results = {tokens: []};
window.addEventListener('message', e => {if(e.data.type === 'auth-token') results.tokens.push(e.data.token)});
for (const [name, action] of Object.entries({
 parent: () => parent.document.body.dataset.secret,
 cookie: () => document.cookie,
 storage: () => localStorage.getItem('private'),
 top: () => {top.location = '/escaped'},
})) {try {results[name] = action()} catch(e) {results[name] = 'blocked'}}
results.popup = window.open('/escaped') === null ? 'blocked' : 'opened';
const ws = new WebSocket('ws://' + location.host + '/private-ws');
ws.onerror = () => {results.websocket = 'blocked'};
ws.onmessage = e => {results.websocket = e.data};
fetch('/private-write', {method:'POST', credentials:'include', mode:'no-cors', body:'attack'});
</script><script type="module" src="/module.js"></script>'''


def upstream(url, **kwargs):
    path = urlparse(url).path
    response = requests.Response()
    response.status_code = 200
    if path == '/module.js':
        response._content = b"import {label} from './nested.js'; document.getElementById('module').textContent=label; window.results.module=true; fetch('/website-dev/api').then(r=>r.json()).then(r=>window.results.fetch=r.ok);"
        mime = 'text/javascript'
    elif path == '/nested.js':
        response._content = b"export const label='Module ready';"
        mime = 'text/javascript'
    elif path == '/api':
        response._content = b'{"ok":true}'
        mime = 'application/json'
    else:
        response._content = preview.encode()
        mime = 'text/html'
    response.headers = {'content-type': mime, 'Set-Cookie': 'injected=bad', 'Access-Control-Allow-Credentials': 'true'}
    response.iter_content = Mock(return_value=[response.content])
    return response


app, sock = create_app({'TESTING': True})
app.register_blueprint(canvas.canvas_bp)
writes = []
@sock.route('/private-ws')
def private_ws(ws):
    writes.append('websocket')
    ws.send('synthetic-private-session')
@app.route('/private-write', methods=['POST'])
def private_write():
    writes.append(True)
    return 'should not run'
@app.route('/')
def parent_page():
    response = Response('<body data-secret="synthetic-parent-secret"><iframe id="canvas-iframe" src="/website-dev/"></iframe></body>', content_type='text/html')
    response.set_cookie('private', 'synthetic-cookie')
    return response

server = make_server('127.0.0.1', 0, app, threaded=True)
thread = Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    with patch.object(canvas.http_requests, 'get', side_effect=upstream), sync_playwright() as playwright:
        options = {'headless': True, 'args': ['--no-sandbox']}
        if os.getenv('CHROMIUM_EXECUTABLE'):
            options['executable_path'] = os.environ['CHROMIUM_EXECUTABLE']
        browser = playwright.chromium.launch(**options)
        page = browser.new_page()
        page.goto(f'http://127.0.0.1:{server.server_port}/')
        page.evaluate("localStorage.setItem('private', 'synthetic-storage'); window.Clerk={session:{getToken: async()=> 'synthetic-jwt'}}")
        frame = page.frames[1]
        frame.wait_for_function('window.results.module && window.results.fetch && window.results.websocket')
        page.evaluate('async () => {const auth={' + push + ',' + sync + '}; await auth._pushAuthTokenToCanvas(); await auth._syncSessionCookie(); clearInterval(auth._sessionCookieInterval);}')
        page.wait_for_timeout(200)
        result = frame.evaluate('window.results')
        assert result == {'tokens': [], 'parent': 'blocked', 'cookie': 'blocked', 'storage': 'blocked', 'top': 'blocked', 'popup': 'blocked', 'module': True, 'fetch': True, 'websocket': 'blocked'}, result
        assert writes == [], writes
        assert page.url.endswith('/') and '/escaped' not in page.url
        assert not any(c['name'] == 'injected' for c in page.context.cookies())
        print('PASS: actual preview route retains inline scripts, ES modules, nested imports and fetch; blocks parent DOM/cookies/storage/navigation/popups/auth-token transfer and API writes')
        browser.close()
finally:
    server.shutdown()
    thread.join(timeout=5)
