const assert = require('node:assert/strict');
const {test} = require('node:test');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const vm = require('node:vm');
const source = readFileSync(join(__dirname,'../../src/app.js'),'utf8');

test('sound dispatch ignores inherited keys and still plays configured sounds',()=>{
    const audio=[];
    const context=vm.createContext({CONFIG:{serverUrl:'https://voice.test'},console:{log(){},warn(){},error(){}},
        Audio:class {constructor(url){this.url=url;this.paused=true;audio.push(this);} play(){return Promise.resolve();}},
    });
    vm.runInContext(source.slice(source.indexOf('const DJSoundboard ='),source.indexOf('// ===== FACE MODULE')),context);
    for(const key of ['__proto__','constructor','toString','valueOf']) {
        context.key=key;
        assert.doesNotThrow(()=>vm.runInContext('DJSoundboard.preload(key); DJSoundboard.play(key)',context));
    }
    assert.equal(audio.length,0);
    vm.runInContext("DJSoundboard.preload('air_horn'); DJSoundboard.play('air_horn')",context);
    assert.equal(audio.length,1);
    assert.equal(audio[0].url,'https://voice.test/sounds/air_horn.mp3');
    assert.equal(audio[0].volume,0.4);
});

test('category reorder preserves prototype-named categories as own data keys',async()=>{
    const start=source.indexOf('async reorderCategory(');
    const end=source.indexOf('filterPages(query)',start);
    const context=vm.createContext({console:{log(){}}});
    vm.runInContext('globalThis.menu = {'+source.slice(start,end)+'};',context);
    const categories=JSON.parse('{"first":{"name":"First"},"__proto__":{"name":"Custom"},"last":{"name":"Last"}}');
    context.menu.manifest={categories};
    let rendered=0;context.menu.render=()=>rendered++;context.menu.setupDragDrop=()=>{};
    await context.menu.reorderCategory('__proto__','first');
    assert.equal(Object.getPrototypeOf(context.menu.manifest.categories),null);
    assert.deepEqual(Object.keys(context.menu.manifest.categories),['__proto__','first','last']);
    assert.equal(context.menu.manifest.categories.__proto__.name,'Custom');
    assert.equal(rendered,1);
});


test('category moves treat prototype names as data and reject inherited pages', async () => {
    const start = source.indexOf('async movePageToCategory(');
    const end = source.indexOf('async reorderCategory(', start);
    const requests = [];
    const context = vm.createContext({CONFIG: {serverUrl: 'https://voice.test'}, console,
        fetch: async (...args) => { requests.push(args); return {}; }});
    vm.runInContext('globalThis.menu = {' + source.slice(start, end) + '};', context);
    const menu = context.menu;
    menu.render = () => {};
    menu.setupDragDrop = () => {};
    for (const category of ['__proto__', 'constructor', 'toString', 'normal']) {
        menu.manifest = {pages: {page: {category: 'old'}}, categories: {old: {pages: ['page']}}};
        await menu.movePageToCategory('page', category);
        assert.equal(Object.getPrototypeOf(menu.manifest.categories), null);
        assert.equal(Object.hasOwn(menu.manifest.categories, category), true);
        assert.deepEqual(Array.from(menu.manifest.categories[category].pages), ['page']);
        assert.deepEqual(menu.manifest.categories.old.pages, []);
        assert.equal(menu.manifest.pages.page.category, category);
        assert.equal(JSON.parse(requests.at(-1)[1].body).category, category);
    }
    const before = requests.length;
    await menu.movePageToCategory('__proto__', 'normal');
    await menu.movePageToCategory('constructor', 'normal');
    await menu.movePageToCategory('page', {});
    assert.equal(requests.length, before);
    assert.equal(Object.prototype.category, undefined);
});
