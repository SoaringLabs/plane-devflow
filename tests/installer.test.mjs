import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { install, inventory } from '../lib/installer.mjs';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const NAME = 'plane-devflow';
const ID = `${NAME}@${NAME}`;
const SKILLS = ['plane-setup', 'plane-start', 'plane-deliver'];

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'plane installer $ & ('));
  const packageRoot = path.join(root, 'npx-cache');
  const stateRoot = path.join(root, 'codex-state');
  fs.mkdirSync(stateRoot);
  fs.writeFileSync(path.join(stateRoot, 'config.toml'), '# user formatting\nmodel = "unchanged"\n');
  fs.writeFileSync(path.join(stateRoot, 'auth.json'), '{"synthetic":"keep"}\n');
  fs.mkdirSync(packageRoot);
  fs.cpSync(path.join(REPO, 'plugins'), path.join(packageRoot, 'plugins'), { recursive: true, filter: p => !p.includes('__pycache__') });
  fs.copyFileSync(path.join(REPO, 'package.json'), path.join(packageRoot, 'package.json'));
  const originalConfig = fs.readFileSync(path.join(stateRoot, 'config.toml'));
  const originalAuth = fs.readFileSync(path.join(stateRoot, 'auth.json'));
  t.after(() => {
    try {
      assert.deepEqual(fs.readFileSync(path.join(stateRoot, 'config.toml')), originalConfig);
      assert.deepEqual(fs.readFileSync(path.join(stateRoot, 'auth.json')), originalAuth);
    } finally { fs.rmSync(root, { recursive: true, force: true }); }
  });
  const state = { marketplaces: [], installed: null, calls: [], failAdd: false, failInstall: false, failDiscovery: false, corruptCache: false };
  const managed = path.join(stateRoot, 'marketplaces', 'plane-devflow-npm');
  const run = async args => {
    state.calls.push(args);
    if (args[0] === '--version') return 'codex-cli 0.163.0';
    if (args.slice(0, 3).join(' ') === 'plugin marketplace list') return JSON.stringify({ marketplaces: state.marketplaces });
    if (args.slice(0, 3).join(' ') === 'plugin marketplace add') {
      if (state.failAdd) throw new Error('registration failed');
      state.marketplaces = [{ name: NAME, root: args[3], marketplaceSource: { sourceType: 'local' } }];
      return '{}';
    }
    if (args.slice(0, 3).join(' ') === 'plugin marketplace upgrade') return '{}';
    if (args[0] === 'plugin' && args[1] === 'add') {
      if (state.failInstall) throw new Error('installation failed');
      const marketplace = state.marketplaces[0];
      const catalog = JSON.parse(fs.readFileSync(path.join(marketplace.root, '.agents/plugins/marketplace.json')));
      const source = path.resolve(marketplace.root, catalog.plugins[0].source.path);
      const manifest = JSON.parse(fs.readFileSync(path.join(source, 'plugin.json')));
      const cache = path.join(stateRoot, 'plugins/cache', NAME, NAME, manifest.version);
      fs.mkdirSync(path.dirname(cache), { recursive: true });
      fs.cpSync(source, cache, { recursive: true });
      if (state.corruptCache) fs.unlinkSync(path.join(cache, 'references/delivery.md'));
      state.installed = { pluginId: ID, version: manifest.version, installed: true, enabled: true, source: { source: 'local', path: source }, cache };
      return JSON.stringify({ installed: true });
    }
    if (args[0] === 'plugin' && args[1] === 'list') return JSON.stringify({ installed: state.installed ? [state.installed] : [] });
    throw new Error(`Unexpected native command: ${args}`);
  };
  const discover = async () => {
    const cache = state.installed.cache;
    const skills = SKILLS.map(name => ({ name: `${NAME}:${name}`, pluginId: ID, enabled: true,
      path: path.join(cache, 'skills', name, 'SKILL.md'), interface: { displayName: name } }));
    if (state.failDiscovery) skills.pop();
    return { data: [{ skills, errors: [] }] };
  };
  const options = { packageRoot, env: { ...process.env, CODEX_HOME: stateRoot }, cwd: root, run, discover };
  return { root, packageRoot, stateRoot, managed, state, options };
}

function nativeWrites(state) { return state.calls.filter(args => args[1] === 'add' || args[2] === 'add'); }

test('fresh install retains a complete persistent source after npx cache removal', async t => {
  const f = fixture(t);
  const expected = inventory(path.join(f.packageRoot, 'plugins', NAME));
  const result = await install(f.options);
  assert.equal(result.payloadFiles, Object.keys(expected).length);
  assert.equal(result.payloadHashesMatch, true);
  assert.equal(result.skills.length, 3);
  assert.equal(result.source, 'npm');
  assert.equal(nativeWrites(f.state).length, 2);
  assert.deepEqual(f.state.calls.find(args => args[2] === 'add'), ['plugin', 'marketplace', 'add', fs.realpathSync(f.managed), '--json']);
  fs.rmSync(f.packageRoot, { recursive: true });
  assert.deepEqual(inventory(f.state.installed.source.path), expected);
  assert.deepEqual(inventory(f.state.installed.cache), expected);
});

test('repeat install reuses the same registration and immutable payload', async t => {
  const f = fixture(t);
  await install(f.options);
  const before = inventory(f.managed);
  await install(f.options);
  assert.deepEqual(inventory(f.managed), before);
  assert.equal(f.state.calls.filter(args => args[2] === 'add').length, 1);
});

test('npm upgrade retains prior payload and its original registration', async t => {
  const f = fixture(t);
  await install(f.options);
  const old = f.state.installed.version;
  for (const file of ['package.json', `plugins/${NAME}/plugin.json`]) {
    const target = path.join(f.packageRoot, file);
    const data = JSON.parse(fs.readFileSync(target)); data.version = '0.8.2'; fs.writeFileSync(target, JSON.stringify(data));
  }
  const result = await install(f.options);
  assert.equal(result.version, '0.8.2');
  assert.equal(f.state.marketplaces[0].root, fs.realpathSync(f.managed));
  assert.ok(fs.existsSync(path.join(f.managed, 'versions', old, 'plugin/plugin.json')));
  assert.equal(f.state.calls.filter(args => args[2] === 'add').length, 1);
});

for (const sourceType of ['local', 'git', undefined]) test(`existing ${sourceType || 'unreported'} source and modifications are preserved`, async t => {
  const f = fixture(t);
  const sourceRoot = path.join(f.root, 'user-source');
  fs.cpSync(f.packageRoot, sourceRoot, { recursive: true });
  fs.mkdirSync(path.join(sourceRoot, '.agents/plugins'), { recursive: true });
  fs.writeFileSync(path.join(sourceRoot, '.agents/plugins/marketplace.json'), JSON.stringify({ plugins: [{ source: { path: `./plugins/${NAME}` } }] }));
  const localFile = path.join(sourceRoot, 'plugins', NAME, 'references/delivery.md');
  fs.appendFileSync(localFile, '\nUser-owned customization.\n');
  const before = inventory(sourceRoot);
  f.state.marketplaces = [{ name: NAME, root: sourceRoot, marketplaceSource: { sourceType } }];
  const result = await install(f.options);
  assert.equal(result.existingSourcePreserved, true);
  assert.equal(result.source, sourceType || 'existing');
  assert.deepEqual(inventory(sourceRoot), before);
  assert.equal(fs.existsSync(f.managed), false);
  assert.equal(nativeWrites(f.state).length, 1);
  assert.equal(f.state.calls.some(args => args.includes('remove')), false);
  assert.equal(f.state.calls.filter(args => args.includes('upgrade')).length, sourceType === 'git' ? 1 : 0);
});

test('check mode verifies without registration or installation writes', async t => {
  const f = fixture(t);
  await install(f.options);
  f.state.calls = [];
  const before = inventory(f.managed);
  await install({ ...f.options, checkOnly: true });
  assert.equal(nativeWrites(f.state).length, 0);
  assert.deepEqual(inventory(f.managed), before);
});

test('newer installer can check an older managed installation without upgrading it', async t => {
  const f = fixture(t); const installed = await install(f.options);
  for (const file of ['package.json', `plugins/${NAME}/plugin.json`]) {
    const target = path.join(f.packageRoot, file);
    const data = JSON.parse(fs.readFileSync(target)); data.version = '0.8.2'; fs.writeFileSync(target, JSON.stringify(data));
  }
  f.state.calls = [];
  const result = await install({ ...f.options, checkOnly: true });
  assert.equal(result.version, installed.version); assert.equal(result.installerVersion, '0.8.2');
  assert.equal(nativeWrites(f.state).length, 0);
});

test('registration failure stops installation and a later retry recovers', async t => {
  const f = fixture(t); f.state.failAdd = true;
  await assert.rejects(install(f.options), /registration failed/);
  assert.equal(f.state.calls.some(args => args[1] === 'add'), false);
  assert.equal(fs.existsSync(path.join(f.managed, '.install.lock')), false);
  f.state.failAdd = false;
  assert.equal((await install(f.options)).installed, true);
});

test('installation failure retains the source and releases its lock for retry', async t => {
  const f = fixture(t); f.state.failInstall = true;
  await assert.rejects(install(f.options), /installation failed/);
  assert.equal(fs.existsSync(path.join(f.managed, '.install.lock')), false);
  assert.ok(fs.existsSync(path.join(f.managed, '.agents/plugins/marketplace.json')));
  f.state.failInstall = false;
  assert.equal((await install(f.options)).installed, true);
});

test('missing native skill fails verification rather than reporting success', async t => {
  const f = fixture(t); f.state.failDiscovery = true;
  await assert.rejects(install(f.options), /did not all load/);
  f.state.failDiscovery = false;
  assert.equal((await install({ ...f.options, checkOnly: true })).skills.length, 3);
});

test('missing installed reference is detected even when all three skills load', async t => {
  const f = fixture(t); f.state.corruptCache = true;
  await assert.rejects(install(f.options), /payload differs/);
});

test('unowned directory is never adopted or overwritten', async t => {
  const f = fixture(t);
  fs.mkdirSync(f.managed, { recursive: true }); fs.writeFileSync(path.join(f.managed, 'user.txt'), 'preserve');
  await assert.rejects(install(f.options));
  assert.equal(fs.readFileSync(path.join(f.managed, 'user.txt'), 'utf8'), 'preserve');
  assert.equal(nativeWrites(f.state).length, 0);
});

test('modified managed version is preserved instead of silently replaced', async t => {
  const f = fixture(t); await install(f.options);
  const target = path.join(f.state.installed.source.path, 'references/delivery.md');
  fs.appendFileSync(target, '\nLocal changes.\n'); f.state.calls = [];
  await assert.rejects(install(f.options), /local modifications/);
  assert.match(fs.readFileSync(target, 'utf8'), /Local changes/);
  assert.equal(nativeWrites(f.state).length, 0);
});

test('managed directory symlink is rejected before writing outside its root', async t => {
  const f = fixture(t); await install(f.options);
  const versions = path.join(f.managed, 'versions');
  const outside = path.join(f.root, 'outside'); fs.mkdirSync(outside);
  fs.rmSync(versions, { recursive: true }); fs.symlinkSync(outside, versions, process.platform === 'win32' ? 'junction' : 'dir');
  f.state.calls = [];
  await assert.rejects(install(f.options), /regular directory/);
  assert.deepEqual(fs.readdirSync(outside), []);
  assert.equal(nativeWrites(f.state).length, 0);
});

test('active lock is respected and dead process lock can be recovered', async t => {
  const f = fixture(t); await install(f.options);
  const lock = path.join(f.managed, '.install.lock');
  const owner = { owner: 'plane-devflow/npm-installer/v1', pid: process.pid, host: os.hostname() };
  fs.writeFileSync(lock, JSON.stringify(owner));
  await assert.rejects(install(f.options), /installation is active/);
  fs.writeFileSync(lock, JSON.stringify({ ...owner, pid: 2_147_483_647 }));
  assert.equal((await install(f.options)).installed, true);
});

test('invalid marketplace metadata cannot trigger a write', async t => {
  const f = fixture(t); f.state.marketplaces = [{ name: NAME }];
  await assert.rejects(install(f.options), /invalid Plane marketplace root/);
  assert.equal(nativeWrites(f.state).length, 0);
});

test('help and version run without a Codex process', () => {
  const cli = path.join(REPO, 'bin/plane-devflow.mjs');
  assert.match(execFileSync(process.execPath, [cli, '--help'], { encoding: 'utf8' }), /--check/);
  assert.equal(execFileSync(process.execPath, [cli, '--version'], { encoding: 'utf8' }).trim(), JSON.parse(fs.readFileSync(path.join(REPO, 'package.json'))).version);
});
