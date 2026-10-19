const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');

function load(directory, copy) {
  const module = { exports: {} };
  const context = {
    module, process, console, Buffer,
    require(name) {
      if (name === 'os') return { tmpdir: () => directory };
      if (name === 'child_process') return {
        execSync() { throw new Error('Import must not run Docker'); },
        execFileSync: copy
      };
      return require(name);
    }
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../../inject-device-identity.js'), 'utf8'), context);
  return module.exports.copyStagedFiles;
}

function temporary(t) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'identity-tests-'));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  return directory;
}

for (const failAt of [0, 1, -1]) {
  test(`staging is private and removed after copy outcome ${failAt}`, t => {
    const directory = temporary(t);
    const calls = [];
    const copy = load(directory, (command, args) => {
      assert.equal(command, 'docker');
      assert.equal(args[0], 'cp');
      const source = args[1];
      assert.equal(path.dirname(path.dirname(source)), directory);
      if (process.platform !== 'win32') {
        assert.equal(fs.statSync(path.dirname(source)).mode & 0o777, 0o700);
        assert.equal(fs.statSync(source).mode & 0o777, 0o644);
      }
      calls.push([fs.readFileSync(source, 'utf8'), args[2]]);
      if (calls.length - 1 === failAt) throw new Error('copy failed');
    });
    const operation = () => copy('container-id', [
      { content: 'pairing-token', destination: '/root/.openclaw/devices/paired.json' },
      { content: '{}\n', destination: '/root/.openclaw/devices/pending.json' }
    ]);
    if (failAt < 0) {
      operation();
      assert.deepEqual(calls, [
        ['pairing-token', 'container-id:/root/.openclaw/devices/paired.json'],
        ['{}\n', 'container-id:/root/.openclaw/devices/pending.json']
      ]);
    } else assert.throws(operation, /copy failed/);
    assert.deepEqual(fs.readdirSync(directory), []);
  });
}

test('predictable preexisting files are untouched and shell characters stay literal', t => {
  const root = temporary(t);
  const directory = path.join(root, 'space $() `literal` "quotes"');
  fs.mkdirSync(directory);
  const sentinel = path.join(directory, 'ovu-paired.json');
  fs.writeFileSync(sentinel, 'existing');
  const copy = load(directory, (command, args) => {
    assert.equal(command, 'docker');
    assert.equal(args.length, 3);
    assert.equal(fs.readFileSync(args[1], 'utf8'), 'identity');
    assert.equal(args[2], 'container-id:/app/runtime/uploads/.device-identity.json');
  });
  copy('container-id', [{ content: 'identity', destination: '/app/runtime/uploads/.device-identity.json' }]);
  assert.equal(fs.readFileSync(sentinel, 'utf8'), 'existing');
  assert.deepEqual(fs.readdirSync(directory), ['ovu-paired.json']);
});
