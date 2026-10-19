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
