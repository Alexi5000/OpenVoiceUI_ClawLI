const assert = require('node:assert/strict');
const { test } = require('node:test');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const vm = require('node:vm');

function source(file, start, end) {
    const html = readFileSync(join(__dirname, '../../default-pages', file), 'utf8');
    return html.slice(html.indexOf(start), html.indexOf(end, html.indexOf(start)));
}
function element(tag) {
    return { tag, children: [], dataset: {}, listeners: {},
        append(...children) { this.children.push(...children); },
        addEventListener(event, fn) { this.listeners[event] = fn; },
        set innerHTML(value) { throw new Error('gallery metadata must not enter an HTML parser'); },
    };
}

test('gallery treats hostile image names and URLs as data while retaining all actions', () => {
    const calls = [];
    const context = { document: { createElement: element } };
    for (const name of ['openLightbox', 'useLightboxUrlAsRef', 'copyUrl', 'downloadFromUrl', 'removeFromGallery']) {
        context[name] = (...args) => calls.push([name, ...args]);
    }
    vm.createContext(context);
    vm.runInContext(source('ai-image-creator.html', 'function _galleryCard', 'async function loadGallery'), context);
    for (const entry of [
        { url: '/images/normal.png', name: 'Normal image' },
        { url: '/x" onerror="globalThis.pwned=1', name: "\\');globalThis.pwned=1;//<img src=x onerror=alert(1)>" },
    ]) {
        const card = context._galleryCard(entry);
        const image = card.children[0].children[0];
        const [label, actions] = card.children[1].children;
        assert.equal(image.src, entry.url);
        assert.equal(image.alt, entry.name);
        assert.equal(label.textContent, entry.name);
        image.listeners.click();
        actions.children.forEach(button => button.listeners.click());
        assert.deepEqual(calls.splice(0), [
            ['openLightbox', entry.url, entry.name],
            ['useLightboxUrlAsRef', entry.url, entry.name],
            ['copyUrl', entry.url],
            ['downloadFromUrl', entry.url, entry.name + '.png'],
            ['removeFromGallery', entry.url, card],
        ]);
        assert.equal(context.pwned, undefined);
    }
});

test('icon cards and modal escape attribute data and bind copy without inline metadata', () => {
    const nodes = new Map();
    const document = { getElementById(id) {
        if (!nodes.has(id)) nodes.set(id, { style: {}, classList: { add() {} }, addEventListener(event, fn) { this[event] = fn; } });
        return nodes.get(id);
    } };
    const icon = { url: '/x" onerror="alert(1)\\\'payload', name: '<img src=x>', tenant: 'x', prompt: '<script>bad</script>' };
    const copies = [];
    const context = { document, allIcons: [icon], copyUrl: value => copies.push(value) };
    vm.createContext(context);
    vm.runInContext(source('icon-library.html', 'function esc(', 'async function loadIcons'), context);
    vm.runInContext(source('icon-library.html', 'function render()', 'function onSearchInput'), context);
    vm.runInContext(source('icon-library.html', 'function openModal(', 'function closeModal'), context);
    context.render();
    context.openModal(0);
    for (const id of ['grid', 'modal-body']) {
        const html = nodes.get(id).innerHTML;
        assert.ok(html.includes('src="/x&quot; onerror=&quot;alert(1)'));
        assert.ok(!html.includes('src="/x"'));
        assert.ok(!html.includes("onclick=\"copyUrl('"));
    }
    nodes.get('modal-copy').click();
    assert.deepEqual(copies, [icon.url]);
});
