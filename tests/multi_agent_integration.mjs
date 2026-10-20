// Real Skills CLI installation and optional native host inspection; no model credentials.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import spawn from 'cross-spawn';
import { discoverSkills, inventory } from '../lib/installer.mjs';
import { withNativeSkillHome } from './native_profile_fixture.mjs';
import { createCredentialIsolation, credentialEnvironment, profileMetadata } from './credential_isolation.mjs';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'plane multi agent ')));
const names = ['plane-setup', 'plane-start', 'plane-deliver'];
const hosts = { codex: '.agents/skills', 'claude-code': '.claude/skills', cursor: '.agents/skills', opencode: '.agents/skills' };
const endpoint = 'https://mcp.plane.so/http/mcp';
const realHome = os.homedir();
const protectedPaths = ['.codex/config.toml', '.codex/auth.json', '.claude.json', '.claude/settings.json', '.claude/.credentials.json',
  '.cursor/mcp.json', '.cursor/cli-config.json', '.config/opencode/opencode.json', '.local/share/opencode/auth.json', '.npmrc'];
const digest = file => fs.existsSync(file) ? crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex') : null;
const protectedFiles = protectedPaths.map(file => path.join(realHome, file));
const before = profileMetadata(protectedFiles);
const isolation = createCredentialIsolation(root, { protectedFiles });
isolation.assertProtected();
const write = (file, value) => { fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`); };
function profile(host) {
  const home = path.join(root, host, 'home');
  const project = path.join(root, host, 'project');
  const state = path.join(home, '.codex');
  for (const folder of [home, project, state]) fs.mkdirSync(folder, { recursive: true });
  fs.writeFileSync(path.join(state, 'config.toml'), 'cli_auth_credentials_store = "file"\nmcp_oauth_credentials_store = "file"\n');
  write(path.join(home, '.claude/settings.json'), { env: { PLANE_INSTALL_TEST: 'preserve' } });
  write(path.join(home, '.cursor/mcp.json'), { mcpServers: { retained: { url: 'https://example.invalid/mcp' } } });
  write(path.join(home, '.config/opencode/opencode.json'), { $schema: 'https://opencode.ai/config.json', mcp: {
    retained: { type: 'remote', url: 'https://example.invalid/mcp', enabled: false } } });
  write(path.join(home, '.local/share/opencode/auth.json'), {});
  write(path.join(project, '.plane-devflow.json'), { fixture: 'business mapping remains untouched' });
  const env = credentialEnvironment(root, home);
  return { host, home, project, state, env };
}
function run(label, command, args, target, { optional = false, timeout = 90_000 } = {}) {
  const all = [...isolation.prefix, command, ...args];
  const result = spawn.sync(all[0], all.slice(1), { cwd: target.project, env: target.env, encoding: 'utf8', timeout, maxBuffer: 12 * 1024 * 1024 });
  const record = { command, args, status: result.status, stdout: result.stdout || '', stderr: result.stderr || '', error: result.error?.message };
  write(path.join(root, `${target.host}-${label}.json`), record);
  if (!optional) assert.equal(result.status, 0, `${target.host}/${label}: ${result.error?.message || result.stderr || result.stdout}`);
  return record;
}
async function codexSkills(target) {
  const env = isolation.discoveryEnvironment(target.env);
  return withNativeSkillHome(target.home, () => discoverSkills({ cwd: target.project, env }));
}

const source = path.join(root, 'candidate');
fs.cpSync(path.join(repo, 'skills'), path.join(source, 'skills'), { recursive: true,
  filter: p => !p.includes('__pycache__') && !p.endsWith('.pyc') });
const cli = ['--yes', 'skills@1.7.4'];
const installSource = process.env.PLANE_SKILLS_SOURCE || source;
const expected = Object.fromEntries(names.map(name => [name, inventory(path.join(repo, 'skills', name))]));
const summary = { candidateOnly: installSource === source, source: installSource === source ? 'isolated local snapshot' : installSource, modelExecutionVerified: false, oauthCompleted: false, agents: {} };
try {
  for (const [host, globalDirectory] of Object.entries(hosts)) {
    const target = profile(host);
    const saved = [path.join(target.state, 'config.toml'), path.join(target.home, '.claude/settings.json'),
      path.join(target.home, '.cursor/mcp.json'), path.join(target.home, '.config/opencode/opencode.json'),
      path.join(target.home, '.local/share/opencode/auth.json'), path.join(target.project, '.plane-devflow.json')];
    const initial = saved.map(digest);
    const args = [...cli, 'add', installSource, '--skill', ...names, '--agent', host, '--global', '--yes'];
    run('global-install', 'npx', args, target);
    run('global-repeat', 'npx', args, target);
    for (const name of names) {
      const skill = path.join(target.home, globalDirectory, name);
      assert.deepEqual(inventory(fs.realpathSync(skill)), expected[name]);
      run(`helper-${name}`, process.env.PYTHON || 'python3', [path.join(skill, 'scripts/plane_workflow.py'), '--version'], target);
    }
    assert.deepEqual(saved.map(digest), initial);
    const projectRoot = host === 'claude-code' ? '.claude/skills' : '.agents/skills';
    run('project-install', 'npx', [...cli, 'add', installSource, '--skill', ...names, '--agent', host, '--yes'], target);
    for (const name of names) assert.deepEqual(inventory(fs.realpathSync(path.join(target.project, projectRoot, name))), expected[name]);
    assert.deepEqual(saved.map(digest), initial);
    const result = { globalInstallation: true, projectInstallation: true, repeatedInstallation: true,
      allThreePayloadsAndHelpers: true, configurationAndSyntheticAuthPreserved: true,
      nativeSkillDiscovery: 'not_run', nativeMcpConfiguration: 'not_run', modelExecution: 'unverified', oauth: 'unverified' };
    if (host === 'codex') {
      const loaded = await codexSkills(target); write(path.join(root, 'codex-native-skills.json'), loaded);
      const found = loaded.data.flatMap(x => x.skills).filter(x => names.includes(x.name));
      assert.deepEqual([...new Set(found.map(x => x.name))].sort(), [...names].sort());
      assert.ok(found.every(x => x.enabled && x.dependencies.tools[0].url === endpoint));
      result.nativeSkillDiscovery = 'passed';
      fs.appendFileSync(path.join(target.state, 'config.toml'), `\n[mcp_servers.plane]\nurl = "${endpoint}"\n`);
      const native = run('native-mcp', 'codex', ['--no-daemon', 'mcp', 'get', 'plane', '--json'], target);
      assert.equal(JSON.parse(native.stdout).transport.url, endpoint); result.nativeMcpConfiguration = 'passed';
    } else if (host === 'claude-code' && process.env.PLANE_CLAUDE_BIN) {
      const exe = process.env.PLANE_CLAUDE_BIN;
      result.version = run('version', exe, ['--version'], target).stdout.trim();
      run('mcp-add-retained', exe, ['mcp', 'add', '--scope', 'user', '--transport', 'http', 'retained', 'https://example.invalid/mcp'], target);
      run('mcp-add-plane', exe, ['mcp', 'add', '--scope', 'user', '--transport', 'http', 'plane', endpoint], target);
      assert.match(run('mcp-get-plane', exe, ['mcp', 'get', 'plane'], target).stdout, /mcp\.plane\.so/);
      assert.match(run('mcp-retained', exe, ['mcp', 'get', 'retained'], target).stdout, /example\.invalid/);
      result.nativeMcpConfiguration = 'passed';
      const native = run('native-skills', exe, ['--print', 'List installed skill names only.', '--output-format', 'stream-json', '--verbose',
        '--max-turns', '1', '--no-session-persistence', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}'], target, { optional: true, timeout: 30_000 });
      const events = native.stdout.split('\n').flatMap(line => { try { return [JSON.parse(line)]; } catch { return []; } });
      const init = events.find(x => x.type === 'system' && x.subtype === 'init');
      if (init && names.every(name => (init.skills || init.slash_commands || []).includes(name))) result.nativeSkillDiscovery = 'passed';
      else result.nativeSkillDiscovery = 'unverified_no_authenticated_model_session';
    } else if (host === 'cursor' && process.env.PLANE_CURSOR_BIN) {
      const exe = process.env.PLANE_CURSOR_BIN;
      result.version = run('version', exe, ['--version'], target).stdout.trim();
      const file = path.join(target.home, '.cursor/mcp.json'); const config = JSON.parse(fs.readFileSync(file));
      config.mcpServers.plane = { url: endpoint }; write(file, config);
      const native = run('native-mcp', exe, ['mcp', 'list'], target, { optional: true, timeout: 40_000 });
      if (native.status === 0 && /^plane:\s+requires_authentication\s*$/m.test(native.stdout + native.stderr)) {
        result.nativeMcpConfiguration = 'passed'; result.mcpAuthentication = 'requires_authentication';
      }
      else result.nativeMcpConfiguration = 'unverified_client_login_or_approval_required';
      const scan = run('native-skills', exe, ['--print', '--mode', 'ask', '--output-format', 'stream-json',
        'List installed skills without executing any tools.'], target, { optional: true, timeout: 20_000 });
      result.nativeSkillDiscovery = 'unverified_client_login_required';
      result.nativeSessionExit = scan.status;
      assert.equal(JSON.parse(fs.readFileSync(file)).mcpServers.retained.url, 'https://example.invalid/mcp');
    } else if (host === 'opencode' && process.env.PLANE_OPENCODE_BIN) {
      const exe = process.env.PLANE_OPENCODE_BIN;
      result.version = run('version', exe, ['--version'], target).stdout.trim();
      const native = run('native-skills', exe, ['debug', 'skill'], target, { timeout: 60_000 });
      const found = JSON.parse(native.stdout); assert.ok(names.every(name => found.some(x => x.name === name)));
      result.nativeSkillDiscovery = 'passed';
      const file = path.join(target.home, '.config/opencode/opencode.json'); const config = JSON.parse(fs.readFileSync(file));
      config.mcp.plane = { type: 'remote', url: endpoint, enabled: true }; write(file, config);
      const nativeConfig = JSON.parse(run('native-config', exe, ['debug', 'config'], target).stdout);
      assert.equal(nativeConfig.mcp.plane.url, endpoint); assert.equal(nativeConfig.mcp.retained.url, 'https://example.invalid/mcp');
      result.nativeMcpConfiguration = 'passed';
      const status = run('native-mcp', exe, ['mcp', 'list'], target, { optional: true, timeout: 40_000 });
      result.mcpStatusExit = status.status;
    }
    // Native config changes are intentional only inside this host's temporary profile.
    assert.equal(digest(path.join(target.project, '.plane-devflow.json')), initial.at(-1));
    const nativeConfigFiles = [...saved, path.join(target.home, '.claude.json'), path.join(target.home, '.claude/.claude.json')];
    const nativeConfigHashes = nativeConfigFiles.map(digest);
    run('remove-global', 'npx', [...cli, 'remove', ...names, '--agent', host, '--global', '--yes'], target);
    assert.deepEqual(nativeConfigFiles.map(digest), nativeConfigHashes);
    result.removalPreservesMcpAndAuth = true;
    result.removalPreservesBusinessMapping = digest(path.join(target.project, '.plane-devflow.json')) === initial.at(-1);
    summary.agents[host] = result;
    console.log(`${host}: ${JSON.stringify(result)}`);
  }
  assert.deepEqual(profileMetadata(protectedFiles), before);
  summary.originalProfileMetadataUnchanged = true; summary.evidence = root;
  write(path.join(root, 'summary.json'), summary);
  console.log(JSON.stringify(summary, null, 2));
} catch (error) { console.error(`Multi-agent evidence retained at ${root}`); throw error; }
