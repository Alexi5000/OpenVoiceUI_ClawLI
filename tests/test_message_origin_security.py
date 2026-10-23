from pathlib import Path
import re
import subprocess


def test_message_bridges_reject_foreign_origins_and_unrelated_frames():
    sources = [Path('src/app.js'), Path('src/admin.html'), Path('default-faces/template.html')]
    sources.extend(Path('default-pages').glob('*.html'))
    sources.append(Path('default-pages/retired/website-creator.html'))
    checks = []
    for path in sources:
        for guard in re.findall(r'if\s*\([^\n]*\.origin\s*!==\s*window.location.origin[^\n]*return;', path.read_text()):
            if 'document.getElementById' in guard or 'window.parent' in guard or path.name == 'admin.html':
                checks.append(guard)
    assert len(checks) >= 11
    script = '''
const assert = require('node:assert/strict');
const trusted = {};
const window = {location: {origin: 'https://voice.example'}, parent: trusted};
const document = {getElementById: () => ({contentWindow: trusted})};
'''
    for guard in checks:
        script += '\n{\nfunction accepts(e) { const event=e; ' + guard + ' return true; }\n'
        script += '''
assert.equal(accepts({origin: 'https://evil.example', source: trusted}), undefined);
assert.equal(accepts({origin: 'null', source: trusted}), undefined);
assert.equal(accepts({origin: 'https://voice.example', source: trusted}), true);
'''
        if '.source' in guard:
            script += "assert.equal(accepts({origin: 'https://voice.example', source: {}}), undefined);\n"
        script += '}\n'
    subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)


def test_grid_order_message_targets_only_same_origin_parent():
    source = Path('default-pages/grid-creator.html').read_text()
    start = source.index('async function placeOrder()')
    end = source.index('function etaText(', start)
    script = """
const assert = require('node:assert/strict');
const messages = [];
const fields = {brief: {value: 'private brief'}, count: {value: '3'}, aspect: {value: '1:1'}, orderBtn: {}};
const $ = key => fields[key];
const window = {location: {origin: 'https://voice.test'}, parent: {postMessage: (...args) => messages.push(args)}};
const uuid = () => 'order-1';
let gridType = 'logo', layout = 'separate', chosenRefs = [];
const fetch = async () => ({});
const renderRefs = () => {};
const loadJobs = () => {};
const setTimeout = () => {};
""" + source[start:end] + """
placeOrder().then(() => {
    assert.equal(messages.length, 1);
    assert.equal(messages[0][1], 'https://voice.test');
    assert.ok(messages[0][0].text.includes('private brief'));
});
"""
    subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)
