import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {serializeLogData} from '../../src/security/log-data.mjs';

test('log data escapes record separators and terminal controls, keeping values recoverable', () => {
    const value = ['label', 'hello\r\nFORGED\0\x1b[31m\u2028\u2029', {ok: true}];
    const encoded = serializeLogData(value);
    assert.deepEqual(JSON.parse(encoded), value);
    assert.doesNotMatch(encoded, /[\r\n\0\x1b\u2028\u2029]/);
});

test('diagnostic logging tolerates circular objects, bigint and hostile toJSON', () => {
    const circular = {id: 3n};
    circular.self = circular;
    assert.deepEqual(JSON.parse(serializeLogData(circular)), {id: '3', self: '[Circular]'});
    assert.doesNotThrow(() => serializeLogData({toJSON() {throw Error('private');}}));
    assert.equal(serializeLogData(undefined), '"[Unserializable log data]"');
});

test('sound dispatch logs hostile names through the encoder without invoking inherited entries', () => {
    const source = readFileSync(new URL('../../src/app.js', import.meta.url), 'utf8');
    const messages = [];
    const context = vm.createContext({serializeLogData, CONFIG: {serverUrl: 'https://voice.test'},
        console: {log: (...args) => messages.push(args), warn: (...args) => messages.push(args), error() {}},
        Audio: class {}});
    vm.runInContext(source.slice(source.indexOf('const DJSoundboard ='), source.indexOf('// ===== FACE MODULE')), context);
    context.name = 'unknown\r\nFORGED\u2028';
    vm.runInContext('DJSoundboard.play(name)', context);
    assert.equal(messages.length, 1);
    assert.deepEqual(JSON.parse(messages[0][0]), ['Unknown sound:', context.name]);
    assert.doesNotMatch(messages[0][0], /[\r\n\u2028]/);
});
