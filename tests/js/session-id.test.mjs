import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { createSessionId } from '../../src/security/session-id.mjs';

const helper = readFileSync(new URL('../../src/security/session-id.mjs', import.meta.url), 'utf8').replace('export ', '');
const assignments = ['../../src/app.js', '../../src/core/VoiceSession.js'].flatMap(path => {
    const source = readFileSync(new URL(path, import.meta.url), 'utf8');
    return [...source.matchAll(/this\.sessionId = (createSessionId\(\)|`session_[^`]+`);/g)].map(match => match[1]);
});

test('all voice session creation paths consume 128 cryptographic random bits', () => {
    assert.equal(assignments.length, 3);
    for (const expression of assignments) {
        let bytesRequested = 0;
        const context = vm.createContext({
            crypto: { getRandomValues(bytes) { bytesRequested += bytes.length; bytes.fill(0xab); return bytes; } },
            Math: { random() { throw new Error('predictable randomness used'); } },
            Date: { now: () => 12345 },
        });
        vm.runInContext(helper, context);
        assert.equal(vm.runInContext(expression, context), 'session_12345_' + 'ab'.repeat(16));
        assert.equal(bytesRequested, 16);
    }
});

test('missing or failed secure randomness stops session creation without fallback', () => {
    for (const crypto of [undefined, { getRandomValues() { throw new Error('entropy unavailable'); } }]) {
        const context = vm.createContext({ crypto });
        vm.runInContext(helper, context);
        for (const expression of assignments) assert.throws(() => vm.runInContext(expression, context));
    }
});

test('real session IDs preserve the timestamp prefix and have distinct random suffixes', () => {
    const ids = Array.from({ length: 100 }, createSessionId);
    assert.equal(new Set(ids).size, 100);
    ids.forEach(id => assert.match(id, /^session_\d+_[a-f0-9]{32}$/));
});
