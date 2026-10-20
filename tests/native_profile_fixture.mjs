// Windows' native Known Folder API ignores HOME/USERPROFILE overrides. Only an
// explicitly disposable CI user may mount the isolated skill fixture there.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';

export async function withNativeSkillHome(home, inspect) {
  if (process.platform !== 'win32') return inspect();
  assert.ok(process.env.GITHUB_ACTIONS === 'true' && process.env.PLANE_DISPOSABLE_WINDOWS_PROFILE === '1',
    'Windows native discovery requires an explicitly disposable CI user; real user profiles are preserved.');
  const nativeRoot = path.join(os.homedir(), '.agents', 'skills');
  const isolatedRoot = path.join(home, '.agents', 'skills');
  // Never replace a directory, dangling link, or another test's fixture.
  let present = false;
  try { fs.lstatSync(nativeRoot); present = true; } catch (error) { if (error.code !== 'ENOENT') throw error; }
  assert.equal(present, false, 'Native user skill directory already exists; preserve it.');
  if (!fs.existsSync(isolatedRoot)) return inspect();
  fs.mkdirSync(path.dirname(nativeRoot), { recursive: true });
  fs.symlinkSync(isolatedRoot, nativeRoot, 'junction');
  try { return await inspect(); }
  finally {
    assert.ok(fs.lstatSync(nativeRoot).isSymbolicLink(), 'Fixture link changed; preserve it for inspection.');
    fs.unlinkSync(nativeRoot);
  }
}
