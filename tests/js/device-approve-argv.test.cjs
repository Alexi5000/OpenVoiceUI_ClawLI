const assert = require('node:assert/strict');
const { test } = require('node:test');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const vm = require('node:vm');

const source = readFileSync(join(__dirname, '../../auto-approve-devices.js'), 'utf8');

async function invoke(results) {
  const calls = [];
  const logs = [];
  const context = {
    require(name) {
      assert.equal(name, 'child_process');
      return { execFileSync(file, args, options) {
        calls.push({ file, args: Array.from(args), options });
        const result = results.shift();
        if (result instanceof Error) throw result;
        return result;
      } };
    },
    process: { env: { TEST_VALUE: '$(false); & %PATH% "quotes"' } },
    console: { log(...args) { logs.push(args.join(' ')); } },
    setTimeout(resolve) { resolve(); },
  };
  vm.createContext(context);
  await vm.runInContext(source, context);
  return { calls, logs };
}

test('approval script uses literal docker argv without a shell', async () => {
  const { calls, logs } = await invoke(['APPROVED:1']);
  assert.equal(calls.length, 1);
  const { file, args, options } = calls[0];
  assert.equal(file, 'docker');
  assert.deepEqual(args.slice(0, -1), [
    'compose', '-f', 'docker-compose.yml', '-f', 'docker-compose.local.yml',
    'exec', '-T', 'openclaw', 'node', '-e',
  ]);
  assert.ok(args.at(-1).includes("require('fs')"));
  assert.equal(options.shell, undefined);
  assert.equal(options.timeout, 15000);
  assert.equal(options.env.MSYS_NO_PATHCONV, '1');
  assert.equal(options.env.TEST_VALUE, '$(false); & %PATH% "quotes"');
  assert.ok(logs.some(line => line.includes('Auto-approved 1 device')));
});

test('container script preserves pending device data and approval output', async () => {
  const { calls } = await invoke(['APPROVED:1']);
  const writes = new Map();
  const hostile = 'quoted " $(touch /tmp/never-run); & %PATH%';
  const pending = { request: { deviceId: 'device-1', publicKey: hostile, name: hostile } };
  const containerLogs = [];
  vm.runInNewContext(calls[0].args.at(-1), {
    require(name) {
      assert.equal(name, 'fs');
      return {
        readFileSync(path) { return JSON.stringify(path.endsWith('pending.json') ? pending : {}); },
        writeFileSync(path, data) { writes.set(path, data); },
      };
    },
    console: { log(value) { containerLogs.push(value); } },
  });
  const paired = JSON.parse(writes.get('/root/.openclaw/devices/paired.json'));
  assert.equal(paired['device-1'].publicKey, hostile);
  assert.equal(paired['device-1'].name, hostile);
  assert.deepEqual(paired['device-1'].scopes, ['operator.admin', 'operator.read', 'operator.write']);
  assert.equal(writes.get('/root/.openclaw/devices/pending.json'), '{}');
  assert.deepEqual(containerLogs, ['APPROVED:1']);
});

test('already-paired result stops without retries', async () => {
  const { calls, logs } = await invoke(['ALREADY_PAIRED:2']);
  assert.equal(calls.length, 1);
  assert.ok(logs.some(line => line.includes('Device already paired (2 device')));
});

test('failed container calls and empty state retain retry behavior', async () => {
  const { calls, logs } = await invoke([new Error('container starting'), 'APPROVED:0', 'APPROVED:1']);
  assert.equal(calls.length, 3);
  assert.ok(logs.some(line => line.includes('Auto-approved 1 device')));
});
