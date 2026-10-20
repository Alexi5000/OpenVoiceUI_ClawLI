const assert = require('node:assert/strict');
const { test } = require('node:test');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const vm = require('node:vm');

function element(tag = 'div') {
  return {
    tag, children: [], style: {}, listeners: {}, classes: [],
    classList: { add(value) { this.values = [...(this.values || []), value]; } },
    append(...nodes) { this.children.push(...nodes); },
    appendChild(node) { this.children.push(node); },
    replaceChildren(...nodes) { this.children = nodes; },
    addEventListener(name, handler) { this.listeners[name] = handler; },
    set innerHTML(value) { throw new Error('Unexpected HTML parsing: ' + value); },
  };
}

function setup() {
  const html = readFileSync(join(__dirname, '../../default-pages/voice-studio.html'), 'utf8');
  const nodes = {};
  const calls = [];
  const context = {
    document: { createElement: element },
    $: id => (nodes[id] ||= element()),
    window: { quickTest: (...args) => calls.push(args), libTest: (...args) => calls.push(args) },
    platformLabel: value => value,
    escHtml: value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;'),
    cloneResults: [], allVoices: [],
  };
  vm.createContext(context);
  for (const name of ['showResults', 'renderVoiceLibrary']) {
    const start = html.indexOf('  function ' + name + '()');
    const end = html.indexOf('\n  }', start) + 4;
    vm.runInContext(html.slice(start, end), context);
  }
  return { context, nodes, calls };
}

const hostileId = "');globalThis.pwned=true;//";
const hostileName = '<img src=x onerror=alert(1)>';
const hostileProvider = 'provider" onclick="alert(1)';

test('clone result metadata remains text and Test retains exact provider and voice', () => {
  const { context, nodes, calls } = setup();
  context.cloneResults = [
    { provider: hostileProvider, voice_id: hostileId, clone_time_ms: 1200, status: 'ready' },
    { provider: 'other', voice_id: 'other', status: hostileName },
  ];
  context.showResults();
  const rows = nodes.resultsBody.children;
  assert.equal(rows[0].children[0].textContent, hostileProvider);
  assert.equal(rows[0].children[1].textContent, hostileId);
  assert.equal(rows[0].children[2].textContent, '1.2s');
  assert.equal(rows[1].children[3].children[0].textContent, hostileName);
  assert.equal(rows[1].children[3].children[0].className, 'status-badge');
  const [button, audio] = rows[0].children[4].children;
  button.listeners.click();
  assert.deepEqual(calls[0], [hostileProvider, hostileId, button]);
  assert.equal(audio.controls, true);
  assert.equal(audio.id, 'audio-result-' + hostileProvider);
  context.showResults();
  assert.equal(nodes.resultsBody.children.length, 2);
  assert.equal(context.pwned, undefined);
});

test('voice library names and IDs stay literal and Test retains original identifiers', () => {
  const { context, nodes, calls } = setup();
  context.allVoices = [{ name: hostileName, provider: hostileProvider, voice_id: hostileId }];
  context.renderVoiceLibrary();
  const card = nodes.voiceLibrary.children[0].children[0];
  assert.equal(card.children[0].textContent, hostileName);
  assert.equal(card.children[1].textContent, hostileProvider);
  assert.equal(card.children[2].textContent, hostileId);
  assert.equal(card.children[2].title, hostileId);
  card.children[3].listeners.click();
  assert.deepEqual(calls[0], [hostileProvider, hostileId, card.children[3]]);
  assert.equal(card.children[4].controls, true);
  assert.equal(context.pwned, undefined);
});
