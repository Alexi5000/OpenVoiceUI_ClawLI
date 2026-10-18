from pathlib import Path
import subprocess


def test_file_explorer_navigation_keeps_names_out_of_executable_markup():
    source = Path('default-pages/file-explorer.html').read_text()
    breadcrumb = source.split('function updateBreadcrumb(path)', 1)[1].split('/* LOAD DIRECTORY */', 1)[0]
    shortcuts = source.split('async function buildQuickAccess()', 1)[1].split('/* MARKDOWN RENDERER */', 1)[0]
    script = r'''
const assert = require('node:assert/strict');
class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.style = {}; this.listeners = {}; this.textContent = ''; }
  set innerHTML(value) { throw new Error('Navigation must not generate executable HTML'); }
  appendChild(child) { this.children.push(child); }
  replaceChildren(...children) { this.children = children; }
  addEventListener(type, callback) { this.listeners[type] = callback; }
  click() { this.listeners.click(); }
}
const elements = {breadcrumb: new Element('div'), 'st-path': new Element('span'), 'qa-sites': new Element('div')};
const document = {createElement: tag => new Element(tag), getElementById: id => elements[id]};
const calls = [];
const navigate = path => calls.push(path);
const names = ['normal-website', "x\\');globalThis.__pwned=1;('", 'evil" onmouseover="globalThis.__pwned=1" data-x="', 'été-site'];
const fetch = async () => ({headers: {get: () => 'application/json'}, json: async () => ({entries: [...names.map(name => ({name, type: 'dir'})), {name: 'ignored.old', type: 'dir'}]})});
''' + 'function updateBreadcrumb(path)' + breadcrumb + 'async function buildQuickAccess()' + shortcuts + r'''
(async () => {
  for (const name of names) {
    updateBreadcrumb('Websites/' + name + '/images');
    const parts = elements.breadcrumb.children.filter(el => el.className === 'bc-part');
    assert.deepEqual(parts.map(el => el.textContent), ['My Files', 'Websites', name, 'images']);
    for (const part of parts) part.click();
    assert.deepEqual(calls.splice(0), ['', 'Websites', 'Websites/' + name, 'Websites/' + name + '/images']);
  }
  updateBreadcrumb('');
  assert.equal(elements.breadcrumb.children.length, 1);
  await buildQuickAccess();
  const items = elements['qa-sites'].children;
  assert.equal(items.length, 8);
  for (let i = 0; i < names.length; i++) {
    items[i * 2].click(); items[i * 2 + 1].click();
    assert.deepEqual(calls.splice(0), ['Websites/' + names[i] + '/public/images', 'Websites/' + names[i] + '/ai']);
    assert.equal(items[i * 2].children[1].textContent, names[i].replace(/-website$/, '').replace(/-web-\d+$/, '').replace(/-/g, ' ') + ' images');
  }
  assert.equal(globalThis.__pwned, undefined);
})().catch(error => {console.error(error); process.exit(1);});
'''
    subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)
