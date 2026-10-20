// Actual upstream Skills CLI and native Codex loader. All user/state paths are temporary.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import { fileURLToPath, pathToFileURL } from 'node:url';
import spawn from 'cross-spawn';
import { discoverSkills, inventory } from '../lib/installer.mjs';
import { withNativeSkillHome } from './native_profile_fixture.mjs';
import { createCredentialIsolation, credentialEnvironment, profileMetadata } from './credential_isolation.mjs';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'plane skills add ')));
const names = ['plane-setup', 'plane-start', 'plane-deliver'];
const endpoint = 'https://mcp.plane.so/http/mcp';
const digest = file => fs.existsSync(file) ? crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex') : null;
const realHome = os.homedir();
const realState = process.env.CODEX_HOME || path.join(realHome, '.codex');
const protectedFiles = [path.join(realState, 'config.toml'), path.join(realState, 'auth.json'), path.join(realHome, '.npmrc')];
const before = profileMetadata(protectedFiles);
const isolation = createCredentialIsolation(root, { protectedFiles });
isolation.assertProtected();
function profile(label) {
  const home = path.join(root, label, 'home');
  const state = path.join(home, '.codex');
  const project = path.join(root, label, 'project');
  for (const directory of [home, state, project]) fs.mkdirSync(directory, { recursive: true });
  fs.writeFileSync(path.join(state, 'config.toml'), 'cli_auth_credentials_store = "file"\nmcp_oauth_credentials_store = "file"\n[analytics]\nenabled = false\n');
  const env = credentialEnvironment(root, home);
  return { home, state, project, env };
}
function run(label, command, args, target, { json = false, cwd = target.project, oauthPending = false } = {}) {
  const all = [...isolation.prefix, command, ...args];
  const result = spawn.sync(all[0], all.slice(1), { cwd, env: target.env, encoding: 'utf8',
    timeout: oauthPending ? 20_000 : 180_000, maxBuffer: 16 * 1024 * 1024 });
  fs.writeFileSync(path.join(root, `${label}.json`), JSON.stringify({ command, args, status: result.status,
    stdout: result.stdout, stderr: result.stderr, error: result.error?.message }, null, 2));
  if (oauthPending && result.status !== 0) {
    assert.equal(result.error?.code, 'ETIMEDOUT', `${label}: unexpected registration failure`);
    assert.match(result.stdout, /Added global MCP server 'plane'/);
    assert.match(result.stdout, /OAuth/);
  } else assert.equal(result.status, 0, `${label}: ${result.error?.message || result.stderr || result.stdout}`);
  return json ? JSON.parse(result.stdout) : result.stdout;
}
async function loaded(label, target, expected) {
  const env = isolation.discoveryEnvironment(target.env);
  const result = await withNativeSkillHome(target.home, () => discoverSkills({ cwd: target.project, env }));
  fs.writeFileSync(path.join(root, `${label}.json`), JSON.stringify(result, null, 2));
  const skills = result.data.flatMap(item => item.skills).filter(skill => names.includes(skill.name));
  assert.deepEqual(skills.map(skill => skill.name).sort(), [...expected].sort());
  assert.ok(skills.every(skill => skill.enabled && !skill.pluginId));
  const displayNames = { 'plane-setup': 'Set Up Plane', 'plane-start': 'Start Plane Task', 'plane-deliver': 'Deliver Plane Task' };
  assert.ok(result.data.every(item => !item.errors?.length));
  for (const skill of skills) {
    assert.equal(skill.interface.displayName, displayNames[skill.name]);
    assert.equal(skill.dependencies.tools[0].url, endpoint);
    assert.equal(skill.dependencies.tools[0].transport, 'streamable_http');
  }
  return skills;
}
const global = profile('global');
const snapshot = path.join(root, 'source');
for (const folder of ['skills', 'plugins', '.agents']) fs.cpSync(path.join(repo, folder), path.join(snapshot, folder),
  { recursive: true, filter: source => !source.split(path.sep).includes('__pycache__') && !source.endsWith('.pyc') });
fs.copyFileSync(path.join(repo, 'LICENSE'), path.join(snapshot, 'LICENSE'));
const cli = ['--yes', 'skills@1.7.4'];
const args = ['add', pathToFileURL(snapshot).href, '--skill', ...names, '--agent', 'codex', '--global', '--yes'];
try {
  run('snapshot-git-init', 'git', ['init', '--initial-branch=main', snapshot], global);
  run('snapshot-git-add', 'git', ['-C', snapshot, 'add', '.'], global);
  run('snapshot-git-commit', 'git', ['-C', snapshot, '-c', 'user.name=Installation Test', '-c', 'user.email=test@example.invalid',
    'commit', '--no-gpg-sign', '-m', 'Isolated unpublished candidate'], global);
  const originalConfig = digest(path.join(global.state, 'config.toml'));
  run('skills-cli-version', 'npx', [...cli, '--version'], global);
  run('candidate-discovery', 'npx', [...cli, 'add', snapshot, '--list'], global);
  run('global-install', 'npx', [...cli, ...args], global);
  const native = await loaded('global-native-loader', global, names);
  const expected = Object.fromEntries(names.map(name => [name, inventory(path.join(repo, 'skills', name))]));
  for (const skill of native) {
    assert.deepEqual(inventory(path.dirname(skill.path)), expected[skill.name]);
    run(`runtime-${skill.name}`, process.env.PYTHON || 'python3', [path.join(path.dirname(skill.path), 'scripts/plane_workflow.py'), '--version'], global);
  }
  assert.equal(digest(path.join(global.state, 'config.toml')), originalConfig);
  assert.deepEqual(run('mcp-before', 'codex', ['--no-daemon', 'mcp', 'list', '--json'], global, { json: true }), []);
  run('repeat-install', 'npx', [...cli, ...args], global);
  const updateProbe = run('global-update-check', 'npx', [...cli, 'update', ...names, '--global', '--yes'], global);
  // file:// fixtures are not GitHub-tracked installations in the upstream updater.
  assert.match(updateProbe, /No installed skills found|cannot be checked automatically/);
  const changedPath = path.join(snapshot, 'skills/plane-start/references/workflow.md');
  const originalReference = fs.readFileSync(changedPath);
  fs.appendFileSync(changedPath, '\nSynthetic installation update marker.\n');
  run('snapshot-update-add', 'git', ['-C', snapshot, 'add', '.'], global);
  run('snapshot-update-commit', 'git', ['-C', snapshot, '-c', 'user.name=Installation Test', '-c', 'user.email=test@example.invalid',
    'commit', '--no-gpg-sign', '-m', 'Synthetic source update'], global);
  run('changed-source-reinstall', 'npx', [...cli, ...args], global);
  assert.match(fs.readFileSync(path.join(global.home, '.agents/skills/plane-start/references/workflow.md'), 'utf8'),
    /Synthetic installation update marker/);
  fs.writeFileSync(changedPath, originalReference);
  run('snapshot-restore-add', 'git', ['-C', snapshot, 'add', '.'], global);
  run('snapshot-restore-commit', 'git', ['-C', snapshot, '-c', 'user.name=Installation Test', '-c', 'user.email=test@example.invalid',
    'commit', '--no-gpg-sign', '-m', 'Restore reviewed candidate'], global);
  run('restored-source-reinstall', 'npx', [...cli, ...args], global);
  assert.equal(digest(path.join(global.state, 'config.toml')), originalConfig);
  fs.rmSync(snapshot, { recursive: true }); fs.rmSync(global.env.npm_config_cache, { recursive: true });
  await loaded('after-source-and-cache-removal', global, names);
  for (const name of names) assert.deepEqual(inventory(path.join(global.home, '.agents/skills', name)), expected[name]);

  const project = profile('project');
  run('project-selected-install', 'npx', [...cli, 'add', path.join(repo, 'skills/plane-start'), '--skill', 'plane-start', '--agent', 'codex', '--yes'], project);
  await loaded('project-selected-loader', project, ['plane-start']);
  assert.equal(fs.existsSync(path.join(project.home, '.agents/skills/plane-start')), false);
  for (const name of names) {
    const selected = profile(`only-${name}`);
    run(`selected-${name}`, 'npx', [...cli, 'add', path.join(repo, 'skills', name), '--agent', 'codex', '--global', '--yes'], selected);
    await loaded(`selected-native-${name}`, selected, [name]);
  }
  let transportProbe = { performed: false };
  const liveMcp = process.env.PLANE_LIVE_MCP_PROBE === '1';
  if (liveMcp) {
    // Registration succeeds before Codex waits for human OAuth. End that empty-profile wait.
    run('mcp-register', 'codex', ['--no-daemon', 'mcp', 'add', 'plane', '--url', endpoint], global, { oauthPending: true });
    const response = await fetch(endpoint, { method: 'POST', signal: AbortSignal.timeout(30_000),
      headers: { 'Content-Type': 'application/json', Accept: 'application/json, text/event-stream' },
      body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'initialize', params: {
        protocolVersion: '2025-03-26', capabilities: {}, clientInfo: { name: 'plane_skills_validation', version: '1' } } }) });
    assert.equal(response.status, 401);
    assert.match(response.headers.get('www-authenticate'), /resource_metadata=/);
    transportProbe = { performed: true, httpStatus: response.status, oauthChallenge: true, credentialsSent: false };
    fs.writeFileSync(path.join(root, 'mcp-transport.json'), JSON.stringify(transportProbe, null, 2));
    await response.body?.cancel();
  } else {
    fs.appendFileSync(path.join(global.state, 'config.toml'), `\n[mcp_servers.plane]\nurl = "${endpoint}"\n`);
  }
  const mcp = run('mcp-readback', 'codex', ['--no-daemon', 'mcp', 'get', 'plane', '--json'], global, { json: true });
  assert.equal(mcp.transport.url, endpoint); assert.equal(mcp.enabled, true);
  const mcpHash = digest(path.join(global.state, 'config.toml'));
  run('remove-global-skills', 'npx', [...cli, 'remove', ...names, '--agent', 'codex', '--global', '--yes'], global);
  await loaded('after-skill-removal', global, []);
  assert.equal(digest(path.join(global.state, 'config.toml')), mcpHash);
  assert.equal(fs.existsSync(path.join(global.state, 'auth.json')), false);
  assert.deepEqual(profileMetadata(protectedFiles), before);
  const summary = { upstreamSkillsVersion: '1.7.4', candidateOnly: true, localGitSource: true, globalInstallation: true,
    projectSelectedInstallation: true, eachSkillAlone: true, repeat: true, changedGitSourceReinstall: true,
    upstreamAutomaticUpdateVerified: false, upstreamUpdateLimit: 'file source has no GitHub tracking; public candidate is unpublished',
    sourceAndCacheRemoval: true,
    nativeSkills: native, mcpDependencyParsed: true, skillsCliDoesNotRegisterMcp: true,
    nativeMcpConfigurationReadback: true, registrationViaNativeCommand: liveMcp, transportProbe,
    removalPreservesMcp: true, oauthPerformed: false,
    originalProfileMetadataUnchanged: true, evidence: root };
  fs.writeFileSync(path.join(root, 'summary.json'), JSON.stringify(summary, null, 2));
  console.log(JSON.stringify(summary, null, 2));
} catch (error) { console.error(`Skills CLI integration evidence retained at ${root}`); throw error; }
