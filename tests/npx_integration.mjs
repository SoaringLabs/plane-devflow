// Actual npm tarball -> npx -> Codex -> native skill loader. No model/OAuth session.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import spawn from 'cross-spawn';
import { inventory } from '../lib/installer.mjs';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'plane npx integration ')));
const version = JSON.parse(fs.readFileSync(path.join(repo, 'package.json'))).version;
const state = path.join(root, 'state');
const cache = path.join(root, 'npm-cache');
for (const folder of [state, path.join(root, 'project')]) fs.mkdirSync(folder);
for (const name of ['npm-userconfig', 'npm-globalconfig']) fs.writeFileSync(path.join(root, name), '');
const original = 'cli_auth_credentials_store = "file"\nmcp_oauth_credentials_store = "file"\n[analytics]\nenabled = false\n';
fs.writeFileSync(path.join(state, 'config.toml'), original);
const env = { ...process.env, CODEX_HOME: state, npm_config_cache: cache,
  npm_config_userconfig: path.join(root, 'npm-userconfig'), npm_config_globalconfig: path.join(root, 'npm-globalconfig'),
  npm_config_registry: 'https://registry.npmjs.org/', npm_config_audit: 'false', npm_config_fund: 'false' };
const digest = file => fs.existsSync(file) ? crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex') : null;
const realState = path.resolve(process.env.CODEX_HOME || path.join(os.homedir(), '.codex'));
const protectedFiles = [path.join(realState, 'config.toml'), path.join(realState, 'auth.json'), path.join(os.homedir(), '.npmrc')];
const before = protectedFiles.map(digest);

function run(label, command, args, childEnv = env, cwd = path.join(root, 'project')) {
  const result = spawn.sync(command, args, { cwd, env: childEnv, encoding: 'utf8', timeout: 180_000, maxBuffer: 16 * 1024 * 1024 });
  fs.writeFileSync(path.join(root, `${label}.json`), JSON.stringify({ command, args, status: result.status, stdout: result.stdout, stderr: result.stderr, error: result.error?.message }, null, 2));
  assert.equal(result.status, 0, `${label}: ${result.error?.message || result.stderr || result.stdout}`);
  return JSON.parse(result.stdout);
}

try {
  const packed = run('pack', 'npm', ['pack', '--json', '--ignore-scripts', '--pack-destination', root], env, repo)[0];
  const expected = inventory(path.join(repo, 'plugins/plane-for-codex'));
  assert.deepEqual(packed.files.filter(file => file.path.startsWith('plugins/')).map(file => file.path).sort(),
    Object.keys(expected).map(name => `plugins/plane-for-codex/${name}`).sort());
  assert.ok(packed.files.every(file => !/(?:^|\/)(?:tests|evals|node_modules|__pycache__|\.env|\.npmrc)(?:\/|$)/.test(file.path)));
  const command = ['--yes', '--package', path.join(root, packed.filename), 'plane-for-codex', '--json'];
  const first = run('fresh', 'npx', command);
  assert.equal(first.version, version); assert.equal(first.source, 'npm'); assert.equal(first.payloadFiles, Object.keys(expected).length);
  assert.deepEqual(first.skills.map(skill => skill.displayName).sort(), ['Set Up Plane', 'Start Plane Task', 'Deliver Plane Task'].sort());
  assert.ok(fs.readFileSync(path.join(state, 'config.toml'), 'utf8').startsWith(original));
  const config = digest(path.join(state, 'config.toml'));
  const persistent = path.join(state, 'marketplaces/plane-for-codex-npm/versions', version, 'plugin');
  assert.deepEqual(inventory(persistent), expected);
  assert.deepEqual(inventory(path.join(state, 'plugins/cache/plane-for-codex/plane-for-codex', version)), expected);
  fs.rmSync(cache, { recursive: true });
  const repeat = run('repeat-after-cache-removal', 'npx', command);
  assert.equal(repeat.version, version); assert.equal(digest(path.join(state, 'config.toml')), config);
  run('check', 'npx', [...command, '--check']);
  assert.equal(digest(path.join(state, 'config.toml')), config);

  const localRoot = path.join(root, 'retained source & (local)');
  fs.mkdirSync(path.join(localRoot, '.agents/plugins'), { recursive: true });
  fs.copyFileSync(path.join(repo, '.agents/plugins/marketplace.json'), path.join(localRoot, '.agents/plugins/marketplace.json'));
  fs.cpSync(path.join(repo, 'plugins/plane-for-codex'), path.join(localRoot, 'plugins/plane-for-codex'), { recursive: true, filter: p => !p.includes('__pycache__') });
  fs.appendFileSync(path.join(localRoot, 'plugins/plane-for-codex/references/delivery.md'), '\nSynthetic local customization.\n');
  const localBefore = inventory(localRoot);
  const localState = path.join(root, 'local-state'); fs.mkdirSync(localState);
  fs.writeFileSync(path.join(localState, 'config.toml'), original);
  const localEnv = { ...env, CODEX_HOME: localState };
  run('register-local', 'codex', ['--no-daemon', 'plugin', 'marketplace', 'add', localRoot, '--json'], localEnv);
  const localResult = run('retained-local', 'npx', command, localEnv);
  assert.equal(localResult.existingSourcePreserved, true);
  // Source type is optional in native output (notably Windows path aliases).
  assert.ok(['local', 'existing'].includes(localResult.source));
  const retained = run('retained-registration', 'codex', ['--no-daemon', 'plugin', 'marketplace', 'list', '--json'], localEnv)
    .marketplaces.find(item => item.name === 'plane-for-codex');
  const retainedDirectory = fs.statSync(retained.root, { bigint: true });
  const originalDirectory = fs.statSync(localRoot, { bigint: true });
  assert.equal(retainedDirectory.dev, originalDirectory.dev);
  assert.equal(retainedDirectory.ino, originalDirectory.ino);
  assert.deepEqual(inventory(localRoot), localBefore);
  assert.equal(fs.existsSync(path.join(localState, 'marketplaces/plane-for-codex-npm')), false);
  assert.deepEqual(protectedFiles.map(digest), before);
  const result = { version, packedFiles: packed.files.length, pluginFiles: first.payloadFiles, fresh: true, repeat: true,
    cacheRemoval: true, check: true, retainedLocalSource: true, nativeSkills: first.skills, originalProfileUnchanged: true, evidence: root };
  fs.writeFileSync(path.join(root, 'summary.json'), `${JSON.stringify(result, null, 2)}\n`);
  console.log(JSON.stringify(result, null, 2));
} catch (error) {
  console.error(`npx integration failed; evidence retained at ${root}`);
  throw error;
}
