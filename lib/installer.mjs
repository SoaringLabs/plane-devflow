import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createInterface } from 'node:readline';
import spawn from 'cross-spawn';

const PACKAGE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const NAME = 'plane-for-codex';
const PLUGIN_ID = `${NAME}@${NAME}`;
const SKILLS = ['plane-setup', 'plane-start', 'plane-deliver'];
const OWNER = 'plane-for-codex/npm-installer/v1';
const MARKER = '.plane-for-codex-installer.json';

function json(file) { return JSON.parse(fs.readFileSync(file, 'utf8')); }
function requireValue(condition, message) { if (!condition) throw new Error(message); }
function canonical(file) { return fs.existsSync(file) ? fs.realpathSync(file) : path.resolve(file); }
function regular(file) {
  const stat = fs.lstatSync(file);
  requireValue(stat.isFile() && !stat.isSymbolicLink(), `Expected a regular file: ${file}`);
}

function directory(root) {
  const stat = fs.lstatSync(root);
  requireValue(stat.isDirectory() && !stat.isSymbolicLink(), `Expected a regular directory: ${root}`);
}

export function inventory(root) {
  directory(root);
  const entries = {};
  function visit(directory) {
    for (const item of fs.readdirSync(directory, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      if (item.name === '__pycache__' || item.name.endsWith('.pyc') || item.name === '.DS_Store') continue;
      const file = path.join(directory, item.name);
      requireValue(!item.isSymbolicLink(), `Symbolic links are not supported in the plugin payload: ${file}`);
      if (item.isDirectory()) visit(file);
      else {
        regular(file);
        entries[path.relative(root, file).split(path.sep).join('/')] = crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
      }
    }
  }
  visit(root);
  return entries;
}

function sameFiles(a, b) {
  const keys = Object.keys(a);
  return keys.length === Object.keys(b).length && keys.every(key => a[key] === b[key]);
}

function validatePayload(root) {
  regular(path.join(root, 'plugin.json'));
  const manifest = json(path.join(root, 'plugin.json'));
  requireValue(manifest.name === NAME && /^\d+\.\d+\.\d+(?:-[\w.-]+)?$/.test(manifest.version), 'Invalid Plane plugin manifest.');
  for (const file of ['mcp.json', 'assets/icon.png', 'scripts/plane_workflow.py', 'scripts/plane_sync.py',
    ...SKILLS.flatMap(skill => [`skills/${skill}/SKILL.md`, `skills/${skill}/agents/openai.yaml`])]) regular(path.join(root, file));
  requireValue(json(path.join(root, 'mcp.json')).mcpServers?.plane?.url === 'https://mcp.plane.so/http/mcp', 'Unexpected Plane MCP endpoint.');
  requireValue(fs.readdirSync(path.join(root, 'skills')).sort().join() === [...SKILLS].sort().join(), 'Unexpected bundled skill inventory.');
  return manifest;
}

export function runCodex(args, { cwd, env, timeout = 120_000 }) {
  return new Promise((resolve, reject) => {
    const child = spawn('codex', ['--no-daemon', ...args], { cwd, env, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '';
    let tooLarge = false;
    const timer = setTimeout(() => { child.kill(); reject(new Error('Codex command timed out. Inspect the configured source before retrying.')); }, timeout);
    child.stdout.on('data', chunk => {
      stdout += chunk;
      if (stdout.length > 8 * 1024 * 1024) { tooLarge = true; child.kill(); }
    });
    // Drain native diagnostics without printing credential-bearing remote errors.
    child.stderr.resume();
    child.on('error', error => {
      clearTimeout(timer);
      reject(new Error(error.code === 'ENOENT' ? 'Codex CLI was not found. Install Codex CLI and put codex on PATH.' : 'Unable to start Codex CLI.'));
    });
    child.on('close', code => {
      clearTimeout(timer);
      if (tooLarge || code !== 0) reject(new Error(`Codex ${args.slice(0, 3).join(' ')} failed${code === null ? '' : ` (exit ${code})`}. Run that command directly to inspect its diagnostics.`));
      else resolve(stdout);
    });
  });
}

export function discoverSkills({ cwd, env, timeout = 45_000 }) {
  return new Promise((resolve, reject) => {
    const child = spawn('codex', ['--no-daemon', 'app-server', '--stdio'], { cwd, env, stdio: ['pipe', 'pipe', 'pipe'] });
    const lines = createInterface({ input: child.stdout });
    let settled = false;
    const finish = (error, result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      lines.close();
      child.stdin.end();
      child.kill();
      if (error) reject(error); else resolve(result);
    };
    const timer = setTimeout(() => finish(new Error('Native skill discovery timed out. Installation may exist; run npx plane-for-codex@latest --check to inspect it.')), timeout);
    const send = message => child.stdin.write(`${JSON.stringify(message)}\n`);
    child.stdin.on('error', () => finish(new Error('Native skill discovery closed unexpectedly.')));
    child.stderr.resume();
    child.on('error', () => finish(new Error('Unable to start the Codex skill loader. Update Codex CLI and retry --check.')));
    child.on('close', () => { if (!settled) finish(new Error('Codex skill loader exited before verification.')); });
    lines.on('line', line => {
      let message;
      try { message = JSON.parse(line); } catch { return finish(new Error('Codex returned invalid skill-loader output.')); }
      if (message.error) return finish(new Error('Native skill discovery failed. Update Codex CLI and retry --check.'));
      if (message.id === 0) {
        send({ method: 'initialized', params: {} });
        send({ method: 'skills/list', id: 1, params: { cwds: [cwd], forceReload: true } });
      } else if (message.id === 1) finish(null, message.result);
    });
    send({ method: 'initialize', id: 0, params: { clientInfo: { name: 'plane_for_codex_installer', version: '1.0.0' }, capabilities: { experimentalApi: true } } });
  });
}

function ensureOwnedRoot(root) {
  fs.mkdirSync(path.dirname(root), { recursive: true });
  if (!fs.existsSync(root)) {
    const staging = fs.mkdtempSync(path.join(path.dirname(root), '.plane-npm-'));
    fs.writeFileSync(path.join(staging, MARKER), `${JSON.stringify({ owner: OWNER })}\n`);
    fs.mkdirSync(path.join(staging, 'versions'));
    try { fs.renameSync(staging, root); }
    catch (error) {
      fs.rmSync(staging, { recursive: true });
      if (!fs.existsSync(root)) throw error;
    }
  }
  const stat = fs.lstatSync(root);
  requireValue(stat.isDirectory() && !stat.isSymbolicLink(), 'The npm marketplace path is not a regular directory. Existing data was preserved.');
  regular(path.join(root, MARKER));
  requireValue(json(path.join(root, MARKER)).owner === OWNER, 'The npm marketplace directory is not owned by this installer. Existing data was preserved.');
  directory(path.join(root, 'versions'));
}

function acquireLock(root) {
  const file = path.join(root, '.install.lock');
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      fs.writeFileSync(file, JSON.stringify({ owner: OWNER, pid: process.pid, host: os.hostname() }), { flag: 'wx' });
      return () => fs.unlinkSync(file);
    } catch (error) {
      if (error.code !== 'EEXIST') throw error;
      regular(file);
      const lock = json(file);
      requireValue(lock.owner === OWNER && Number.isInteger(lock.pid) && lock.pid > 0 && lock.host === os.hostname(), 'An unrecognized installation lock exists. Inspect it before retrying.');
      try { process.kill(lock.pid, 0); }
      catch (error) { if (error.code === 'ESRCH') { fs.unlinkSync(file); continue; } }
      throw new Error('Another Plane plugin installation is active. Retry when it finishes.');
    }
  }
  throw new Error('Could not acquire the plugin installation lock. Retry after inspecting the current process.');
}

function stageBundle(root, bundle, version) {
  const versions = path.join(root, 'versions');
  const destination = path.join(versions, version);
  const expected = inventory(bundle);
  if (!fs.existsSync(destination)) {
    const staging = fs.mkdtempSync(path.join(versions, '.staging-'));
    try {
      fs.cpSync(bundle, path.join(staging, 'plugin'), { recursive: true, filter: source => !source.split(path.sep).includes('__pycache__') && !source.endsWith('.pyc') && !source.endsWith(`${path.sep}.DS_Store`) });
      requireValue(sameFiles(expected, inventory(path.join(staging, 'plugin'))), 'The staged plugin does not match the npm bundle.');
      fs.renameSync(staging, destination);
    } finally { if (fs.existsSync(staging)) fs.rmSync(staging, { recursive: true }); }
  }
  requireValue(sameFiles(expected, inventory(path.join(destination, 'plugin'))), 'This installed version has local modifications. Existing files were preserved; inspect them before retrying.');
  const catalog = { name: NAME, interface: { displayName: 'Plane for Codex' }, plugins: [{ name: NAME, source: { source: 'local', path: `./versions/${version}/plugin` }, policy: { installation: 'AVAILABLE', authentication: 'ON_INSTALL' }, category: 'Productivity' }] };
  const directory = path.join(root, '.agents', 'plugins');
  for (const folder of [path.join(root, '.agents'), directory]) {
    if (!fs.existsSync(folder)) fs.mkdirSync(folder);
    const stat = fs.lstatSync(folder);
    requireValue(stat.isDirectory() && !stat.isSymbolicLink(), 'The npm marketplace metadata path is not a regular directory.');
  }
  const temporary = path.join(directory, `marketplace.${process.pid}.tmp`);
  requireValue(!fs.existsSync(temporary), 'An unfinished marketplace update exists. Inspect it before retrying.');
  fs.writeFileSync(temporary, `${JSON.stringify(catalog, null, 2)}\n`, { flag: 'wx' });
  fs.renameSync(temporary, path.join(directory, 'marketplace.json'));
}

export async function install({ checkOnly = false, cwd = process.cwd(), env = process.env, packageRoot = PACKAGE_ROOT,
  run = runCodex, discover = discoverSkills } = {}) {
  const bundle = path.join(packageRoot, 'plugins', NAME);
  const packaged = validatePayload(bundle);
  requireValue(json(path.join(packageRoot, 'package.json')).version === packaged.version, 'Installer and plugin versions disagree.');
  const options = { cwd: path.resolve(cwd), env };
  await run(['--version'], options);
  const marketplaces = JSON.parse(await run(['plugin', 'marketplace', 'list', '--json'], options)).marketplaces;
  requireValue(Array.isArray(marketplaces), 'Codex returned an invalid marketplace list.');
  let existing = marketplaces.find(item => item.name === NAME);
  requireValue(!existing || typeof existing.root === 'string', 'Codex returned an invalid Plane marketplace root.');
  const stateRoot = canonical(env.CODEX_HOME || path.join(os.homedir(), '.codex'));
  const managedRoot = path.join(stateRoot, 'marketplaces', 'plane-for-codex-npm');
  const usingManaged = existing && canonical(existing.root) === managedRoot;
  let releaseLock;
  let sourceKind = usingManaged ? 'npm' : existing?.marketplaceSource?.sourceType || 'existing';
  try {
    if (!checkOnly) {
      if (!existing || usingManaged) {
        ensureOwnedRoot(managedRoot);
        releaseLock = acquireLock(managedRoot);
        stageBundle(managedRoot, bundle, packaged.version);
        sourceKind = 'npm';
        if (!existing) await run(['plugin', 'marketplace', 'add', managedRoot, '--json'], options);
      }
      if (existing?.marketplaceSource?.sourceType === 'git') {
        await run(['plugin', 'marketplace', 'upgrade', NAME, '--json'], options);
      }
      // Local development checkouts retain their own update policy and registration.
      await run(['plugin', 'add', PLUGIN_ID, '--json'], options);
    }
    const listed = JSON.parse(await run(['plugin', 'list', '--marketplace', NAME, '--json'], options));
    const installed = listed.installed?.find(item => item.pluginId === PLUGIN_ID);
    requireValue(installed?.installed && installed.enabled, 'The Plane plugin is not installed and enabled.');
    if (sourceKind === 'npm' && !checkOnly) requireValue(installed.version === packaged.version, 'Codex installed an unexpected version. Inspect the selected source before retrying.');
    const discovered = await discover(options);
    const skills = (discovered.data || []).flatMap(item => item.skills || []).filter(skill => skill.pluginId === PLUGIN_ID);
    requireValue(skills.length === 3 && SKILLS.every(name => skills.some(skill => skill.name === `${NAME}:${name}` && skill.enabled)), 'The three Plane skills did not all load and enable. Retry --check after inspecting the native plugin.');
    requireValue(!(discovered.data || []).flatMap(item => item.errors || []).some(error => JSON.stringify(error).includes(NAME)), 'The native loader reported a Plane skill error.');
    const cacheRoots = new Set(skills.map(skill => path.dirname(path.dirname(path.dirname(skill.path)))));
    requireValue(cacheRoots.size === 1, 'The Plane skills were loaded from different plugin versions.');
    const cache = [...cacheRoots][0];
    requireValue(canonical(cache) === canonical(path.join(stateRoot, 'plugins', 'cache', NAME, NAME, installed.version)), 'The Plane skills did not load from the native installed cache.');
    const source = sourceKind === 'npm' && !checkOnly ? bundle : installed.source?.path;
    requireValue(typeof source === 'string', 'Codex did not report an inspectable plugin source.');
    const sourceManifest = validatePayload(source);
    requireValue(sourceManifest.version === installed.version && validatePayload(cache).version === installed.version, 'Source and installed plugin versions disagree.');
    const sourceFiles = inventory(source);
    requireValue(sameFiles(sourceFiles, inventory(cache)), 'The installed plugin payload differs from its selected source.');
    return { installed: true, enabled: true, version: installed.version, installerVersion: packaged.version,
      source: sourceKind, existingSourcePreserved: Boolean(existing && !usingManaged), payloadFiles: Object.keys(sourceFiles).length,
      payloadHashesMatch: true, skills: skills.map(skill => ({ name: skill.name, displayName: skill.interface?.displayName, enabled: skill.enabled })) };
  } finally { if (releaseLock) releaseLock(); }
}

export async function main(args = process.argv.slice(2)) {
  const version = json(path.join(PACKAGE_ROOT, 'package.json')).version;
  if (args.length === 1 && ['--help', '-h'].includes(args[0])) {
    console.log(`Plane for Codex ${version}\n\nUsage: npx plane-for-codex@latest [--check] [--json]\n\nInstall the complete plugin, or verify the current installation with --check.\nRequires Node.js 20+ and a plugin-enabled Codex CLI on PATH. Runtime helpers require Python 3.10+.\nExisting marketplace sources and account authorization are preserved.`);
    return;
  }
  if (args.length === 1 && ['--version', '-v'].includes(args[0])) { console.log(version); return; }
  const asJson = args.includes('--json');
  try {
    requireValue(args.every(arg => ['--check', '--json'].includes(arg)), 'Unknown option. Use --help for available commands.');
    const result = await install({ checkOnly: args.includes('--check') });
    if (asJson) console.log(JSON.stringify(result, null, 2));
    else {
      console.log(`Plane for Codex ${result.version} is installed and enabled.\nVerified ${result.payloadFiles} plugin files and all three native skills.`);
      for (const skill of result.skills) console.log(`  ${skill.displayName || skill.name}`);
      if (result.existingSourcePreserved) console.log(result.source === 'git'
        ? 'Refreshed your existing Git marketplace without changing its configured repository or ref.'
        : 'Kept your existing local marketplace source. Update that checkout separately to change its plugin version.');
      if (result.source === 'npm' && result.version !== result.installerVersion) console.log('A different npm bundle is available. Rerun without --check to install the selected bundle.');
      const setup = result.skills.find(skill => skill.name === `${NAME}:plane-setup`);
      console.log(`Open a new Codex chat and select ${setup.displayName || setup.name}. Existing account authorization is retained.`);
    }
  } catch (error) {
    if (asJson) console.error(JSON.stringify({ error: error.message }));
    else console.error(`Plane for Codex: ${error.message}`);
    process.exitCode = 1;
  }
}
