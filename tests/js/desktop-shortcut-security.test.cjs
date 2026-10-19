const assert = require('node:assert/strict');
const { test } = require('node:test');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const vm = require('node:vm');

function element() {
  return { children: [], style: {}, listeners: {},
    append(...nodes) { this.children.push(...nodes); },
    addEventListener(name, fn) { this.listeners[name] = fn; },
  };
}

test('shortcut names and IDs remain data, with live duplicate prevention', async () => {
  const html = readFileSync(join(__dirname, '../../default-pages/desktop.html'), 'utf8');
  const start = html.indexOf('async function createShortcut()');
  const body = element();
  const hostileId = "');globalThis.pwned=true;//";
  const hostileName = '<img src=x onerror=alert(1)>';
  const desktopPages = ['existing'];
  const additions = [];
  const context = {
    fetchManifest: async () => {}, PAGES: {
      [hostileId]: { name: hostileName }, existing: { name: 'Existing' }, hidden: { name: 'Hidden' },
    }, recycleBin: ['hidden'], desktopPages,
    document: { createElement: element },
    createWindow(opts) { assert.equal(opts.content, undefined); return 1; },
    windows: new Map([[1, { el: { querySelector: () => body } }]]),
    addShortcutToDesktop(id, row) { additions.push(id); desktopPages.push(id); },
    getIcon() { return ''; }, getPageIconType() { return ''; },
  };
  vm.createContext(context);
  vm.runInContext(html.slice(start, html.indexOf('function addShortcutToDesktop', start)), context);
  await context.createShortcut();
  const rows = body.children[0].children[1].children;
  assert.equal(rows.length, 2);
  assert.equal(rows[0].children[1].textContent, hostileName);
  assert.equal(rows[1].children[2].textContent, 'on desktop');
  rows[0].listeners.click(); rows[0].listeners.click(); rows[1].listeners.click();
  assert.deepEqual(additions, [hostileId]);
  assert.equal(context.pwned, undefined);
});
