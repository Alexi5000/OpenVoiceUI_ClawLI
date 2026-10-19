const assert = require('node:assert/strict');
const { test } = require('node:test');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const vm = require('node:vm');
const html = readFileSync(join(__dirname, '../../default-pages/bulk-image-uploader.html'), 'utf8');
function section(start, end) { return html.slice(html.indexOf(start), html.indexOf(end, html.indexOf(start))); }
function node() { return { style: {}, listeners: {}, classList: { add() {} },
    get innerHTML() { return this._html ?? String(this.textContent ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); },
    set innerHTML(value) { this._html = value; },
    addEventListener(k, fn) { this.listeners[k] = fn; },
}; }
function fixture() {
    const nodes = new Map();
    const $ = id => { if (!nodes.has(id)) nodes.set(id, node()); return nodes.get(id); };
    const context = vm.createContext({ $, location: { origin: 'https://voice.test' }, files: [], filter: 'all',
        renderTabs() {}, sz: () => '1KB', ago: () => 'now', IC: {aud:'',oth:''}, COLORS: {aud:'red'},
        document: {createElement: node}, updQCt() {},
    });
    vm.runInContext(html.split('\n').find(line=>line.startsWith('function esc(')), context);
    return { context, nodes, $ };
}
test('upload renderer escapes quotes as well as HTML text', () => {
    const { context } = fixture();
    assert.equal(context.esc('"\'<&>'), '&quot;&#39;&lt;&amp;&gt;');
});
test('gallery binds hostile search text as a value, preserving mouse and keyboard actions', () => {
    const {context,$} = fixture();
    const search = "\\');alert(1);//";
    $('srch').value = search;
    context.files = [{name:search,cat:'img',ext:'png',url:'/x" onerror="alert(1)',size:1}];
    const card = node();
    $('grid').querySelectorAll = () => [card];
    const calls=[]; context.lbOpen=(...args)=>calls.push(args);
    vm.runInContext(section('function render(){', '// ── Lightbox'), context);
    context.render();
    assert.ok(!$('grid').innerHTML.includes('onclick="lbOpen'));
    assert.ok($('grid').innerHTML.includes('src="/x&quot; onerror=&quot;alert(1)"'));
    card.listeners.click();
    let prevented=false;
    card.listeners.keydown({key:'Enter',preventDefault(){prevented=true;}});
    assert.equal(prevented,true);
    assert.deepEqual(calls,[[0,'all',search],[0,'all',search]]);
});
test('lightbox and upload copy callbacks preserve URLs without compiling inline JavaScript', () => {
    const {context,$}=fixture();
    const url='/x" onclick="alert(1)';
    const copies=[];context.cpUrl=value=>copies.push(value);
    context.files=[{name:'test',url,cat:'img',size:1,ext:'png'}];
    vm.runInContext(section('function lbOpen(', 'function lbClose('),context);
    context.lbOpen(0,'all','');
    assert.ok(!$('lbBar').innerHTML.includes('onclick="cpUrl'));
    assert.ok($('lbC').innerHTML.includes('&quot;'));
    $('lbCopy').listeners.click();
    let button;
    $('qi1').querySelector=()=>({replaceWith(value){button=value;}});
    vm.runInContext(section('function setQI(', 'function cancelQ('),context);
    context.setQI(1,100,'ok','',{url});
    assert.ok(button);
    assert.ok(!button.innerHTML.includes(url));
    button.listeners.click();
    assert.deepEqual(copies,['https://voice.test'+url,url]);
});
