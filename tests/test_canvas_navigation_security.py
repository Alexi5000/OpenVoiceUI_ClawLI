from pathlib import Path
import subprocess


def test_canvas_navigation_rejects_executable_urls_and_keeps_web_navigation():
    source = Path('src/app.js').read_text()
    resolver = source.split('        function resolveCanvasUrl(url) {', 1)[1].split('\n        // Route abort', 1)[0]
    action = source.split("                        case 'open-url':", 1)[1].split("                        case 'request-auth-token':", 1)[0]
    script = r'''
const assert = require('node:assert/strict');
const window = {location: {href: 'https://voice.example/'}, AGENT_CONFIG: {devsiteMap: {'dev.example': 'https://voice.example/devsite-demo/'}}};
const iframe = {src: 'unchanged'};
const container = {classList: {add() {}, remove() {}}};
const document = {getElementById: id => id === 'canvas-iframe' ? iframe : container};
''' + 'function resolveCanvasUrl(url) {' + resolver + '\nfunction navigate(url) { const event = {data: {}}; switch ("open-url") { case "open-url":' + action + r'''
}}
for (const url of ['javascript:globalThis.__pwned=1', 'JaVaScRiPt:alert(1)', '\tjava\nscript:alert(1)', 'data:text/html,<script>alert(1)</script>', 'vbscript:msgbox(1)', 'file:///etc/passwd', 'blob:https://voice.example/abc', 'https://[invalid', '', null, {}]) {
  assert.equal(resolveCanvasUrl(url), null, String(url));
  navigate(url);
  assert.equal(iframe.src, 'unchanged');
}
for (const url of ['/pages/image-splitter.html?src=%2Fuploads%2Ftest.png', 'https://example.org/page', '//example.org/page', 'http://example.org/page', 'pages/desktop.html']) {
  navigate(url);
  assert.equal(iframe.src, url);
}
navigate('https://dev.example/assets/page');
assert.equal(iframe.src, 'https://voice.example/devsite-demo/assets/page');
iframe.src = 'unchanged';
navigate('http://127.0.0.1/internal');
assert.equal(iframe.src, 'unchanged');
window.AGENT_CONFIG.devsiteMap['dev.example'] = 'javascript:alert(1)//';
navigate('https://dev.example/');
assert.equal(iframe.src, 'unchanged');
assert.equal(globalThis.__pwned, undefined);
'''
    subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)
