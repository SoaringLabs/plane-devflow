import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { createCredentialIsolation, credentialEnvironment, profileMetadata } from './credential_isolation.mjs';

const macOnly = { skip: process.platform !== 'darwin' };
function fixture(t) {
  const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'plane credential boundary ')));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const realHome = path.join(root, 'synthetic-real-home');
  fs.mkdirSync(realHome);
  const isolation = createCredentialIsolation(root, { realHome });
  isolation.assertProtected();
  const { prefix } = isolation;
  const run = (command, args) => spawnSync(prefix[0], [...prefix.slice(1), command, ...args],
    { encoding: 'utf8', timeout: 10_000 });
  return { root, realHome, run };
}

test('blocks security by absolute path and through a descendant shell', macOnly, t => {
  const f = fixture(t);
  const alias = path.join(f.root, 'security-alias');
  fs.symlinkSync('/usr/bin/security', alias);
  // help is deliberately harmless, including when run against the old broken policy.
  for (const [command, args] of [['/usr/bin/security', ['help']], [alias, ['help']],
    ['/bin/sh', ['-c', '/usr/bin/security help']]]) {
    const result = f.run(command, args);
    assert.notEqual(result.status, 0, 'system security command must be denied before it can access credentials');
    assert.match(result.stderr, /Operation not permitted/);
  }
});

test('preserves synthetic real-profile files while allowing disposable profile writes', macOnly, t => {
  const f = fixture(t);
  const secret = path.join(f.realHome, '.claude.json');
  fs.writeFileSync(secret, 'synthetic credential sentinel');
  const before = fs.readFileSync(secret);
  for (const script of ["require('fs').readFileSync(process.argv[1])", "require('fs').writeFileSync(process.argv[1], 'changed')"]) {
    const result = f.run(process.execPath, ['-e', script, secret]);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /EPERM|EACCES/);
  }
  assert.deepEqual(fs.readFileSync(secret), before);
  const temporary = path.join(f.root, 'disposable-auth.json');
  assert.equal(f.run(process.execPath, ['-e', "require('fs').writeFileSync(process.argv[1], 'synthetic')", temporary]).status, 0);
  assert.equal(fs.readFileSync(temporary, 'utf8'), 'synthetic');
});

test('disposable environment excludes inherited credentials and user configuration overrides', t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'plane env '));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const overrides = { OPENAI_API_KEY: 'synthetic', ANTHROPIC_API_KEY: 'synthetic', GITHUB_TOKEN: 'synthetic',
    SSH_AUTH_SOCK: 'synthetic', NODE_OPTIONS: 'synthetic', CLAUDE_CONFIG_DIR: '/synthetic-real-profile',
    npm_config_userconfig: '/synthetic-real-npmrc', CODEX_HOME: '/synthetic-real-codex' };
  const saved = Object.fromEntries(Object.keys(overrides).map(key => [key, process.env[key]]));
  try {
    Object.assign(process.env, overrides);
    const home = path.join(root, 'home');
    const env = credentialEnvironment(root, home);
    for (const key of ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GITHUB_TOKEN', 'SSH_AUTH_SOCK', 'NODE_OPTIONS']) assert.equal(env[key], undefined);
    for (const key of ['HOME', 'CODEX_HOME', 'CLAUDE_CONFIG_DIR', 'XDG_CONFIG_HOME', 'npm_config_userconfig'])
      assert.ok(env[key].startsWith(root + path.sep));
  } finally {
    for (const [key, value] of Object.entries(saved)) {
      if (value === undefined) delete process.env[key]; else process.env[key] = value;
    }
  }
});

test('profile metadata observes changes without reading credential contents', t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'plane metadata '));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const file = path.join(root, 'synthetic-auth.json');
  assert.deepEqual(profileMetadata([file]), [null]);
  fs.writeFileSync(file, 'synthetic');
  const before = profileMetadata([file]);
  fs.chmodSync(file, 0);
  assert.doesNotThrow(() => profileMetadata([file]));
  fs.chmodSync(file, 0o600);
  fs.appendFileSync(file, ' changed');
  assert.notDeepEqual(profileMetadata([file]), before);
});

test('blocks the actual legacy Keychain service and its UI service', macOnly, t => {
  const f = fixture(t);
  const probe = path.join(f.root, 'service-probe');
  const source = fileURLToPath(new URL('./fixtures/keychain_service_probe.c', import.meta.url));
  const built = spawnSync('/usr/bin/clang', [source, '-o', probe], { encoding: 'utf8', timeout: 30_000 });
  assert.equal(built.status, 0, built.stderr);
  for (const service of ['com.apple.SecurityServer', 'com.apple.security.agent']) {
    const result = f.run(probe, [service]);
    assert.equal(result.status, 1, `${service} must be unreachable: ${result.stderr}`);
    assert.equal(result.stdout.trim(), '1100', 'bootstrap lookup must report BOOTSTRAP_NOT_PRIVILEGED');
  }
});
