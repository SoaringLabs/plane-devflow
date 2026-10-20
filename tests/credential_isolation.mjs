// Shared process boundary for disposable native-client integration profiles.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';

export function credentialEnvironment(root, home) {
  for (const name of ['npm-userconfig', 'npm-globalconfig']) fs.writeFileSync(path.join(root, name), '');
  // Deliberate allowlist: no provider tokens, SSH agent, inherited NODE_OPTIONS,
  // or user-selected credential/configuration paths enter a disposable client.
  return { PATH: process.env.PATH, HOME: home, USERPROFILE: home, CODEX_HOME: path.join(home, '.codex'),
    CLAUDE_CONFIG_DIR: path.join(home, '.claude'), XDG_CONFIG_HOME: path.join(home, '.config'),
    XDG_CACHE_HOME: path.join(home, '.cache'), XDG_DATA_HOME: path.join(home, '.local/share'),
    XDG_STATE_HOME: path.join(home, '.local/state'), OPENCODE_CONFIG_DIR: path.join(home, '.config/opencode'),
    OPENCODE_DISABLE_AUTOUPDATE: 'true', OPENCODE_DISABLE_DEFAULT_PLUGINS: 'true', OPENCODE_DISABLE_LSP_DOWNLOAD: 'true',
    OPENCODE_DISABLE_MODELS_FETCH: 'true', CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: '1', DISABLE_AUTOUPDATER: '1',
    NO_OPEN_BROWSER: '1', DISABLE_TELEMETRY: '1', DO_NOT_TRACK: '1', NO_COLOR: '1', CI: 'true', TERM: 'xterm-256color',
    TMPDIR: root, TEMP: root, TMP: root, LANG: 'en_US.UTF-8', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0',
    GCM_INTERACTIVE: 'Never', SystemRoot: process.env.SystemRoot, COMSPEC: process.env.COMSPEC, PATHEXT: process.env.PATHEXT,
    npm_config_cache: path.join(root, 'npm-cache'), npm_config_userconfig: path.join(root, 'npm-userconfig'),
    npm_config_globalconfig: path.join(root, 'npm-globalconfig'), npm_config_registry: 'https://registry.npmjs.org/',
    npm_config_audit: 'false', npm_config_fund: 'false' };
}

// Check existing files without opening credential contents. Synthetic fixture
// files can still use byte hashes in their owning tests.
export function profileMetadata(files) {
  const describe = stat => ['dev', 'ino', 'mode', 'uid', 'gid', 'size', 'mtimeNs', 'ctimeNs']
    .map(key => stat[key].toString());
  return files.map(file => {
    try {
      const link = fs.lstatSync(file, { bigint: true });
      return [describe(link), link.isSymbolicLink() ? describe(fs.statSync(file, { bigint: true })) : null];
    } catch (error) { if (error.code === 'ENOENT') return null; throw error; }
  });
}

export function createCredentialIsolation(root, { realHome = os.homedir(), protectedFiles = [] } = {}) {
  let prefix = [];
  if (process.platform === 'darwin') {
    const quoted = value => JSON.stringify(value);
    const denied = ['.codex/config.toml', '.codex/auth.json', '.claude', '.claude.json', '.cursor', '.config',
      '.agents', '.local/share/opencode', '.npmrc', 'Library/Keychains'];
    const paths = [...denied.map(file => path.join(realHome, file)), ...protectedFiles];
    const rules = `(version 1)\n(allow default)\n` +
      `(deny file-write* (subpath ${quoted(realHome)}) ${paths.map(file => `(subpath ${quoted(file)})`).join(' ')})\n` +
      `(deny file-read* ${paths.map(file => `(subpath ${quoted(file)})`).join(' ')})\n` +
      // securityd's launchd label is NOT its legacy Keychain Mach service name.
      '(deny mach-lookup (global-name "com.apple.SecurityServer") (global-name "com.apple.securityd") ' +
      '(global-name "com.apple.securityd.xpc") (global-name "com.apple.security.agent") (global-name "com.apple.secd"))\n' +
      // Covers absolute paths and subprocesses; PATH stubs alone are bypassable.
      '(deny process-exec (literal "/usr/bin/security"))\n';
    const file = path.join(root, 'credential-isolation.sb');
    fs.writeFileSync(file, rules);
    prefix = ['/usr/bin/sandbox-exec', '-f', file];
  }
  function assertProtected() {
    if (!prefix.length) return;
    const result = spawnSync(prefix[0], [...prefix.slice(1), '/usr/bin/security', 'help'],
      { encoding: 'utf8', timeout: 10_000 });
    assert.notEqual(result.status, 0, 'Credential boundary failed: security must not execute.');
    assert.match(result.stderr || '', /Operation not permitted/, 'Credential sandbox unavailable; stop before starting native clients.');
  }
  function discoveryEnvironment(env) {
    if (!prefix.length) return env;
    const resolved = spawnSync('/usr/bin/which', ['codex'], { env, encoding: 'utf8' });
    assert.equal(resolved.status, 0, 'Codex CLI must be available on the isolated PATH.');
    const directory = path.join(root, 'credential-isolation-bin');
    fs.mkdirSync(directory, { recursive: true });
    const quote = value => `'${value.replaceAll("'", "'\\''")}'`;
    fs.writeFileSync(path.join(directory, 'codex'),
      `#!/bin/sh\nexec ${[...prefix, resolved.stdout.trim()].map(quote).join(' ')} "$@"\n`, { mode: 0o755 });
    return { ...env, PATH: `${directory}${path.delimiter}${env.PATH}` };
  }
  return { prefix, assertProtected, discoveryEnvironment };
}
