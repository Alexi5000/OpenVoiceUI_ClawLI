const assert = require('node:assert/strict');
const { test } = require('node:test');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const vm = require('node:vm');

function element(tag) {
  return {
    tag, children: [],
    replaceChildren(...nodes) { this.children = nodes; },
    set innerHTML(value) { throw new Error('Unexpected HTML parsing: ' + value); },
  };
}

function setup(returnUrl) {
  const source = readFileSync(join(__dirname, '../../routes/registry.py'), 'utf8');
  const msgEl = element('div');
  const timers = [];
  const context = {
    document: { createElement: element }, msgEl, cfg: { returnUrl },
    setTimeout: (fn, ms) => timers.push({ fn, ms }), window: { location: {} },
  };
  for (const name of ['showError', 'showManualBtn']) {
    const start = source.indexOf('        function ' + name + '(');
    const end = source.indexOf('\n        }}', start) + 11;
    const script = source.slice(start, end).replaceAll('{{', '{').replaceAll('}}', '}');
    vm.runInNewContext(script + `\nglobalThis.${name} = ${name};`, context);
  }
  return { context, msgEl, timers };
}

test('manual return URL stays in the link property without HTML parsing', () => {
  const url = 'https://example.test/\"><img src=x onerror=globalThis.pwned=1>';
  const { context, msgEl } = setup(url);
  context.showManualBtn();
  assert.equal(msgEl.children[0].tag, 'a');
  assert.equal(msgEl.children[0].href, url);
  assert.equal(msgEl.children[0].textContent, 'Complete Check-in on Pinokio');
  assert.equal(msgEl.children[1].tag, 'p');
  assert.equal(context.pwned, undefined);
});

test('error detail renders literally and preserves scheduled return redirect', () => {
  const { context, msgEl, timers } = setup('https://example.test/done?existing=1');
  const message = '<img src=x onerror=globalThis.pwned=1>';
  context.showError(message);
  assert.equal(msgEl.children[0].textContent, message);
  assert.equal(msgEl.children[0].className, 'error');
  assert.equal(timers[0].ms, 3000);
  timers[0].fn();
  assert.equal(context.window.location.href, 'https://example.test/done?existing=1&error=checkin_failed');
  assert.equal(context.pwned, undefined);
});
