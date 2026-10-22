"""Explicit, resumable product upgrades. Planning is read-only; stages are independent."""
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from product_release import REPOSITORY, SKILLS, validate_manifest, verify_source, git
from plane_sync import CONFIG_NAME, WorkflowError, require, sync_provider

HOSTS = ('codex', 'claude-code', 'cursor', 'opencode')
HOST_SKILL_FOLDERS = ('.codex/skills', '.claude/skills', '.cursor/skills', '.config/opencode/skills')


def host_entries(base, canonical):
    """Snapshot host entries without following redirects outside the chosen scope."""
    base, canonical = Path(base), Path(canonical)
    entries = {}
    for folder in HOST_SKILL_FOLDERS:
        parent = base / folder
        require(not any(path.is_symlink() for path in (parent, *parent.parents) if path == base or base in path.parents),
                'Host installation parents must not be symlinks; preserve them for review.')
        for name in SKILLS:
            path = parent / name
            if path.is_symlink():
                require(path.resolve() == canonical / name and path.exists(),
                        'Host skill link redirects to another installation; preserve it for review.')
                entry = {'kind': 'canonical_link'}
            else:
                files = inventory(path)
                entry = None if files is None else {'kind': 'copy', 'files': files}
            entries[folder + '/' + name] = entry
    return entries


def verify_host_entries(selected, base, canonical, expected, *, resumed=False):
    current = host_entries(base, canonical)
    for key, previous in selected['host_entries'].items():
        found = current[key]
        # Skills 1.7.4 uses the universal .agents location for the other hosts.
        selected_copy = selected['host'] == 'claude-code' and key.startswith('.claude/skills/')
        name = key.rsplit('/', 1)[1]
        refreshed = found == {'kind': 'canonical_link'} or found == {'kind': 'copy', 'files': expected[name]}
        require(found == previous or (resumed and selected_copy and refreshed),
                'Host skill files changed since review; preserve modifications and plan again.')
    return current


def host_refresh_complete(selected, entries, expected):
    return selected['host'] != 'claude-code' or all(
        entries['.claude/skills/' + name] in ({'kind': 'canonical_link'}, {'kind': 'copy', 'files': expected[name]})
        for name in SKILLS)


def read_skills_lock(path, version):
    path = Path(path)
    require(not path.is_symlink(), 'Skills lock must not be a symlink; preserve it for review.')
    if not path.exists():
        return None
    require(path.is_file(), 'Skills lock must be a regular file.')
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        raise ValueError('Cannot read the existing skills lock; preserve it before installation.') from None
    require(isinstance(data, dict) and type(data.get('version')) is int and data['version'] == version and
            isinstance(data.get('skills'), dict) and all(isinstance(entry, dict) for entry in data['skills'].values()),
            'Unrecognized skills lock; preserve it before installation.')
    return data


def project_lock(root):
    return read_skills_lock(Path(root) / 'skills-lock.json', 1)


def lock_changes_are_scoped(before, after, version):
    original = before or {'version': version, 'skills': {}}
    current = after or {'version': version, 'skills': {}}
    if before is None and version == 3 and 'dismissed' in current:
        # The upstream initial v3 schema adds this empty prompt-state map.
        original['dismissed'] = {}
    return ({key: value for key, value in current.items() if key != 'skills'} ==
            {key: value for key, value in original.items() if key != 'skills'} and
            {key: value for key, value in current['skills'].items() if key not in SKILLS} ==
            {key: value for key, value in original['skills'].items() if key not in SKILLS})


def verify_project_lock(selected, root, *, allow_product_changes=False):
    before, after = selected['project_lock'], project_lock(root)
    if not allow_product_changes:
        require(after == before, 'Skills lock changed since review; preserve it and plan again.')
        return after
    require(lock_changes_are_scoped(before, after, 1),
            'Skills lock contains unrelated changes; preserve them for review.')
    return after


def verify_global_lock(selected, *, allow_product_changes=False):
    lock = selected['global_lock']
    path = Path(lock['path'])
    base = Path(lock['base'])
    require(not any(parent.is_symlink() for parent in path.parents if parent == base or base in parent.parents),
            'Global skills lock parents must not be symlinks.')
    current = read_skills_lock(path, 3)
    require(lock_changes_are_scoped(lock['before'], current, 3) if allow_product_changes else current == lock['before'],
            'Global skills lock changed outside the selected product; preserve it and plan again.')


def verify_installer_environment(selected):
    # Skills 1.7.4 uses cwd/.claude for project installs; CLAUDE_CONFIG_DIR
    # affects only its global Claude target. Universal hosts use HOME/.agents.
    if selected['scope'] != 'global':
        return
    home = Path.home().resolve()
    require(home == Path(selected['target']).parent.parent,
            'The global installation home changed since review; restore the original environment or plan again.')
    state_base = Path(os.environ['XDG_STATE_HOME']).resolve() if os.environ.get('XDG_STATE_HOME') else home
    lock_path = state_base / ('skills/.skill-lock.json' if os.environ.get('XDG_STATE_HOME') else '.agents/.skill-lock.json')
    require(str(lock_path) == selected['global_lock']['path'],
            'The global skills metadata location changed since review; restore the original environment or plan again.')
    if selected['host'] == 'claude-code':
        configured = os.environ.get('CLAUDE_CONFIG_DIR', '').strip()
        require(Path(configured or home / '.claude').resolve() == home / '.claude',
                'The global Claude installation location changed since review; preserve that scope and plan again.')


def preserve_lock_metadata(selected, root):
    """The upstream CLI rewrites its schema; retain non-product metadata exactly."""
    from plane_workflow import atomic_write
    before, after = selected['project_lock'], project_lock(root)
    if before is None:
        verify_project_lock(selected, root, allow_product_changes=True)
        return
    merged = dict(before)
    merged['skills'] = {key: value for key, value in before['skills'].items() if key not in SKILLS}
    merged['skills'].update({key: value for key, value in (after or {'skills': {}})['skills'].items() if key in SKILLS})
    if merged != after:
        atomic_write(Path(root) / 'skills-lock.json', (json.dumps(merged, indent=2) + '\n').encode())


def run_installer(args, root):
    # Call the JS launcher directly; npx.cmd would require a Windows command shell.
    node, launcher = shutil.which('node'), shutil.which('npx')
    require(node and launcher, 'Node.js and npm are required for this installation channel.')
    version = subprocess.run([node, '--version'], capture_output=True, text=True, check=True).stdout.strip().lstrip('v')
    require(tuple(map(int, version.split('.'))) >= (22, 20, 0), 'Skills CLI requires Node.js 22.20 or newer.')
    script = Path(launcher).resolve()
    if script.suffix.lower() == '.cmd':
        script = script.parent / 'node_modules/npm/bin/npx-cli.js'
    require(script.name == 'npx-cli.js' and script.is_file(), 'Cannot resolve the original npm JS launcher; use a manual channel handoff.')
    return subprocess.run([node, str(script), *args[1:]], cwd=root, capture_output=True, text=True, timeout=180)


def baseline_files(source, version, subtree, target):
    from product_release import SEMVER
    require(isinstance(version, str) and SEMVER.fullmatch(version), 'Installed product version is unknown; use a reviewed manual handoff.')
    revision = target['commit'] if version == target['version'] else 'v' + version
    try:
        expected = {}
        for name in git(source, 'ls-tree', '-r', '--name-only', revision, '--', subtree).decode().splitlines():
            expected[name[len(subtree) + 1:]] = hashlib.sha256(git(source, 'show', f'{revision}:{name}')).hexdigest()
        require(bool(expected), 'Installed baseline is absent from the release source.')
        return expected
    except subprocess.CalledProcessError:
        raise ValueError('Cannot verify the historical installation baseline; preserve it for manual review.') from None


def verify_installation_baseline(source, record):
    selected = record['plan']['installation']
    if record['plan']['channel'] == 'plugin':
        versions = {'plugin': selected['version']}
        payloads = {'plugin': selected['before']}
    else:
        versions, payloads = selected['versions'], selected['before']
    for name, version in versions.items():
        subtree = 'plugins/plane-devflow' if name == 'plugin' else 'skills/' + name
        expected = baseline_files(source, version, subtree, record['plan']['target'])
        require(payloads[name] == expected, 'Installed payload is customized or from another source; preserve it for review.')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def inventory(root):
    root = Path(root)
    if not root.exists():
        return None
    require(root.is_dir() and not root.is_symlink(), 'An installation must be a real skill directory.')
    files = {}
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(), 'Customized symlink in skill payload; review before upgrading.')
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def expected_payload(release, prefix):
    return {name[len(prefix) + 1:]: value for name, value in release['files'].items() if name.startswith(prefix + '/')}


def remote_default(root):
    """Discover the activation branch without updating local Git references."""
    import re
    from plane_workflow import run
    output = run(['git', 'ls-remote', '--symref', 'origin', 'HEAD'], root).stdout
    branch = re.search(r'^ref: refs/heads/([^\r\n\t]+)\tHEAD$', output, re.M)
    commit = re.search(r'^([0-9a-f]{40})\tHEAD$', output, re.M)
    require(branch is not None and commit is not None, 'Cannot determine the actual remote default branch; preserve the current project and retry discovery.')
    return {'branch': branch.group(1), 'commit': commit.group(1)}


def installation(project, scope, host, home=None):
    require(scope in ('project', 'global') and host in HOSTS, 'Choose the original scope and a supported agent.')
    home = Path(home or Path.home()).resolve()
    base = home if scope == 'global' else Path(project).resolve()
    target = base / '.agents/skills'
    if scope == 'global' and host == 'claude-code':
        require(Path(os.environ.get('CLAUDE_CONFIG_DIR', '').strip() or home / '.claude').resolve() == home / '.claude',
                'A custom Claude configuration location requires an explicit manual installation handoff.')
    require(not any((base / name).is_symlink() for name in ('.agents', '.agents/skills')), 'Installation parents must not be symlinks.')
    # Capture exact existing contents; apply rechecks this snapshot before installation.
    found = {}
    versions = {}
    for name in SKILLS:
        path = target / name
        found[name] = inventory(path)
        if found[name] is None:
            host_path = {'codex': '.codex/skills', 'claude-code': '.claude/skills', 'cursor': '.cursor/skills',
                         'opencode': '.config/opencode/skills'}[host]
            require(not (base / host_path / name).exists(), 'A host-specific installation already exists; resolve it before adding another distribution.')
        if found[name] is not None:
            try:
                data = json.loads((path / 'distribution.json').read_text())
            except (OSError, ValueError):
                raise ValueError('Existing installation has no product identity; use a reviewed manual handoff.') from None
            require(data.get('generator') == 'plane-devflow/build_skills.py' and data.get('skill') == name,
                    'Existing skill belongs to another source; preserve it.')
            versions[name] = data.get('version')
    entries = host_entries(base, target)
    for key, entry in entries.items():
        if entry is not None:
            name = key.rsplit('/', 1)[1]
            require(found[name] is not None and (entry['kind'] == 'canonical_link' or entry['files'] == found[name]),
                    'Host-specific skill files are customized or unidentified; preserve them for review.')
    tracked = []
    if scope == 'project':
        from plane_workflow import run
        prefixes = ['skills-lock.json', *['.agents/skills/' + name for name in SKILLS],
                    *[folder + '/' + name for folder in ('.codex/skills', '.claude/skills', '.cursor/skills', '.config/opencode/skills') for name in SKILLS]]
        tracked = run(['git', 'ls-files', '--', *prefixes], project).stdout.splitlines()
    global_lock = None
    if scope == 'global':
        state_base = Path(os.environ['XDG_STATE_HOME']).resolve() if os.environ.get('XDG_STATE_HOME') else home
        lock_path = state_base / ('skills/.skill-lock.json' if os.environ.get('XDG_STATE_HOME') else '.agents/.skill-lock.json')
        require(not any(parent.is_symlink() for parent in lock_path.parents if parent == state_base or state_base in parent.parents),
                'Global skills lock parents must not be symlinks.')
        global_lock = {'path': str(lock_path), 'base': str(state_base), 'before': read_skills_lock(lock_path, 3)}
    return {'scope': scope, 'host': host, 'target': str(target), 'versions': versions, 'before': found, 'host_entries': entries,
            'project_lock': project_lock(project) if scope == 'project' else None,
            'global_lock': global_lock,
            'tracked_project_installation': bool(tracked), 'tracked_paths': tracked}


def paths(root, plan_id):
    from plane_workflow import run
    common = Path(run(['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'], root).stdout.strip())
    require(len(plan_id) == 64 and all(c in '0123456789abcdef' for c in plan_id), 'Invalid upgrade plan ID.')
    directory = common / 'plane-devflow/product-upgrades' / plan_id
    require(not any(p.is_symlink() for p in (directory, *directory.parents) if p == common or common in p.parents),
            'Upgrade records must not resolve through symlinks.')
    return directory, directory / 'record.json'


def plan(root, release, *, scope='project', host='codex', channel='skills', home=None, plugin_root=None, expected_plan_id=None, apply=False, candidate_source=False):
    from plane_workflow import repo_config, configuration_lock, atomic_write, run
    from github_setup import config_digest, install
    root, config = repo_config(root)
    target = validate_manifest(release, allow_candidate=candidate_source)
    require(channel in ('skills', 'plugin'), 'Unsupported installation channel.')
    if channel == 'skills':
        selected = installation(root, scope, host, home)
    else:
        require(plugin_root is not None, 'Resolve the original plugin installation before planning its update.')
        plugin_root = Path(plugin_root).resolve()
        require(json.loads((plugin_root / 'plugin.json').read_text()).get('name') == 'plane-devflow', 'Unexpected plugin installation.')
        selected = {'scope': scope, 'host': host, 'target': str(plugin_root), 'before': inventory(plugin_root),
                    'version': json.loads((plugin_root / 'plugin.json').read_text())['version'], 'manual_handoff': True}
    default = remote_default(root)
    base, base_sha = default['branch'], default['commit']
    project_plan = install(root, release=target, upgrade=True, candidate_source=candidate_source)
    spec = {'schema': 1, 'repository': config['github']['repository'], 'workspace': config['plane']['workspace'],
            'project_id': config['plane']['project_id'], 'config_digest': config_digest(config),
            'base': base, 'base_sha': base_sha, 'target': target, 'installation': selected,
            'channel': channel, 'project_plan': project_plan}
    if candidate_source:
        spec['candidate_source'] = True
    plan_id = digest(spec)
    directory, record_path = paths(root, plan_id)
    result = {'plan_id': plan_id, 'status': 'planned', 'plan': spec, 'record_path': str(record_path),
              'record_written': False, 'release_url': f'https://github.com/{REPOSITORY}/releases/tag/{target["tag"]}'}
    if apply:
        require(expected_plan_id == plan_id, 'Save exactly the reviewed plan with --expected-plan-id; target, files or installation may have changed.')
        with configuration_lock(root):
            if record_path.exists():
                previous = json.loads(record_path.read_text())
                require(previous.get('plan') == spec, 'Upgrade record conflicts with the reviewed plan.')
                return status(root, plan_id)
            directory.mkdir(parents=True)
            atomic_write(record_path, (json.dumps({'schema': 1, 'plan': spec, 'source': None, 'project': None,
                                                  'local': 'pending', 'pr': None, 'verification': None}, sort_keys=True) + '\n').encode())
        result['record_written'] = True
    return result


def read(root, plan_id):
    from plane_workflow import repo_config
    from github_setup import config_digest
    root, config = repo_config(root)
    _, record_path = paths(root, plan_id)
    require(record_path.is_file() and not record_path.is_symlink(), 'Save the reviewed upgrade plan first.')
    record = json.loads(record_path.read_text())
    require(record.get('schema') == 1 and digest(record.get('plan')) == plan_id, 'Upgrade plan was modified.')
    require(config_digest(config) == record['plan']['config_digest'], 'Project mapping changed; plan again.')
    validate_manifest(record['plan']['target'], allow_candidate=record['plan'].get('candidate_source', False))
    directory, _ = paths(root, plan_id)
    require(record.get('source') in (None, str(directory / 'source')), 'Unexpected staged source location.')
    project = record.get('project')
    if project and project.get('status') != 'native':
        require(project.get('path') == str(directory / 'project') and
                project.get('branch') == 'codex/plane-devflow-upgrade-' + record['plan']['target']['version'] + '-' + plan_id[:8],
                'Unexpected upgrade checkout identity.')
    if record.get('rollback_workspace'):
        require(record['rollback_workspace'] == str(directory / 'rollback') and
                record.get('rollback', {}).get('branch') == 'codex/plane-devflow-rollback-' + plan_id[:8],
                'Unexpected rollback checkout identity.')
    return root, record


def save(root, plan_id, record):
    from plane_workflow import atomic_write
    _, path = paths(root, plan_id)
    atomic_write(path, (json.dumps(record, sort_keys=True) + '\n').encode())


def staged_coordinator(root, plan_id, current_helper, arguments):
    """Use a fresh process outside the installation that the upgrade replaces."""
    import sys
    root, record = read(root, plan_id)
    if not record['source']:
        return None
    verify_source(record['source'], record['plan']['target'], allow_candidate=record['plan'].get('candidate_source', False))
    helper = Path(record['source']) / 'plugins/plane-devflow/scripts/plane_workflow.py'
    if helper.resolve() == Path(current_helper).resolve():
        return None
    return subprocess.run([sys.executable, str(helper), *arguments], check=False).returncode


def stage(root, plan_id, *, source=None, candidate_source=False, apply=False):
    """Download one fixed commit outside the installation; never execute source hooks."""
    from plane_workflow import configuration_lock
    root, record = read(root, plan_id)
    if not apply:
        return {'plan_id': plan_id, 'status': 'planned', 'next_step': 'stage', 'writes_performed': False}
    directory, _ = paths(root, plan_id)
    target = directory / 'source'
    with configuration_lock(root):
        root, record = read(root, plan_id)
        require(not record['plan'].get('candidate_source') or candidate_source,
                'A candidate plan requires explicit candidate-source staging; it cannot become a stable release.')
        if 'staging_mode' in record:
            require(record['staging_mode'] == ('candidate' if candidate_source else 'stable'),
                    'Resume the original source channel; do not relabel a candidate as a stable release.')
        if record['source']:
            verify_source(record['source'], record['plan']['target'], allow_candidate=record['plan'].get('candidate_source', False))
            return status(root, plan_id)
        if 'staging_mode' not in record:
            record['staging_mode'] = 'candidate' if candidate_source else 'stable'
            save(root, plan_id, record)
        require(record['staging_mode'] == ('candidate' if candidate_source else 'stable'), 'Resume the original source channel; do not relabel a candidate as a stable release.')
        if target.exists():
            verify_source(target, record['plan']['target'], allow_candidate=record['plan'].get('candidate_source', False))
            verify_installation_baseline(Path(source) if source is not None and candidate_source else target, record)
            record.update(source=str(target), candidate_source=candidate_source)
            save(root, plan_id, record)
            return status(root, plan_id)
        # Publish the staging directory only after every byte is verified. A failed
        # clone/copy cannot leave the final source path permanently half populated.
        with tempfile.TemporaryDirectory(prefix='.source-stage-', dir=directory) as temporary:
            staged = Path(temporary) / 'source'
            if source is not None:
                require(candidate_source, 'A local candidate source requires explicit candidate-source mode.')
                source = Path(source).resolve()
                require(git(source, 'rev-parse', 'HEAD').decode().strip() == record['plan']['target']['commit'], 'Candidate commit mismatch.')
                staged.mkdir()
                for name in record['plan']['target']['files']:
                    path = staged / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(git(source, 'show', f'{record["plan"]["target"]["commit"]}:{name}'))
            else:
                require(not record['plan'].get('candidate_source'), 'An isolated candidate test requires its explicit local source.')
                git(directory, '-c', 'core.hooksPath=/dev/null', 'clone', '--no-checkout', '--filter=blob:none',
                    f'https://github.com/{REPOSITORY}.git', str(staged))
                git(staged, '-c', 'core.hooksPath=/dev/null', 'checkout', '--detach', record['plan']['target']['commit'])
                actual = git(staged, 'rev-parse', record['plan']['target']['tag'] + '^{commit}').decode().strip()
                require(actual == record['plan']['target']['commit'], 'Published tag moved since selection.')
            verify_source(staged, record['plan']['target'], allow_candidate=record['plan'].get('candidate_source', False))
            verify_installation_baseline(Path(source) if source is not None else staged, record)
            staged.rename(target)
        record['source'] = str(target)
        record['candidate_source'] = candidate_source
        save(root, plan_id, record)
    return status(root, plan_id)


def ensure_worktree(root, workspace, branch, base):
    """Reconcile a Git operation whose result may have outlived its caller."""
    from plane_workflow import run
    workspace = Path(workspace)
    require(not workspace.is_symlink(), 'Upgrade checkout must not be a symlink.')
    if not workspace.exists():
        existing = run(['git', 'rev-parse', '--verify', 'refs/heads/' + branch], root, check=False)
        if existing.returncode == 0:
            require(existing.stdout.strip() == base, 'Interrupted upgrade branch moved; preserve it for review.')
            run(['git', '-c', 'core.hooksPath=/dev/null', 'worktree', 'add', str(workspace), branch], root)
        else:
            run(['git', '-c', 'core.hooksPath=/dev/null', 'worktree', 'add', '-b', branch, str(workspace), base], root)
    require(Path(run(['git', 'rev-parse', '--show-toplevel'], workspace).stdout.strip()).resolve() == workspace.resolve(),
            'Unexpected upgrade checkout path.')
    require(run(['git', 'branch', '--show-current'], workspace).stdout.strip() == branch and
            run(['git', 'rev-parse', 'HEAD'], workspace).stdout.strip() == base,
            'Interrupted upgrade checkout moved; preserve it for review.')


def prepare_project(root, plan_id, *, apply=False):
    from plane_workflow import run, configuration_lock
    from github_setup import install
    root, record = read(root, plan_id)
    if not apply:
        return {'plan_id': plan_id, 'status': 'planned', 'next_step': 'prepare_project', 'writes_performed': False}
    require(record['source'], 'Stage and verify the target release first.')
    verify_source(record['source'], record['plan']['target'], allow_candidate=record['plan'].get('candidate_source', False))
    directory, _ = paths(root, plan_id)
    with configuration_lock(root):
        root, record = read(root, plan_id)
        if record['project'] and record['project']['status'] != 'workspace_prepared':
            return status(root, plan_id)
        spec = record['plan']
        tracked = spec['channel'] == 'skills' and spec['installation'].get('tracked_project_installation')
        if spec['project_plan']['provider'] == 'native' and not tracked:
            record['project'] = {'status': 'native', 'changes': []}
            save(root, plan_id, record)
            return status(root, plan_id)
        require(remote_default(root) == {'branch': spec['base'], 'commit': spec['base_sha']},
                'Remote default branch changed; refresh the upgrade plan.')
        run(['git', 'fetch', '--', 'origin', spec['base']], root)
        require(run(['git', 'rev-parse', f'origin/{spec["base"]}'], root).stdout.strip() == spec['base_sha'],
                'Default branch moved; refresh the upgrade plan.')
        branch = 'codex/plane-devflow-upgrade-' + spec['target']['version'] + '-' + plan_id[:8]
        workspace = directory / 'project'
        if record['project'] is None:
            record['project'] = {'status': 'workspace_prepared', 'path': str(workspace), 'branch': branch}
            save(root, plan_id, record)
        ensure_worktree(root, workspace, branch, spec['base_sha'])
        require(run(['git', 'branch', '--show-current'], workspace).stdout.strip() == branch, 'Upgrade checkout changed branches.')
        if spec['project_plan']['provider'] == 'native':
            record['project'].update(status='diff_prepared', provider='native', changes={})
            save(root, plan_id, record)
            return status(root, plan_id)
    # install owns its own lock. The identity and target are checked again there.
    change = install(workspace, release=spec['target'], upgrade=True, candidate_source=spec.get('candidate_source', False))
    require(not change['changes'] or change['expected_files_sha256'] == spec['project_plan']['expected_files_sha256'],
            'The selected checkout differs from the reviewed project plan.')
    change = install(workspace, release=spec['target'], upgrade=True, apply=True,
                     expected_files_sha256=change['expected_files_sha256'], candidate_source=spec.get('candidate_source', False))
    with configuration_lock(root):
        root, record = read(root, plan_id)
        record['project'].update(status='diff_prepared', changes=change['changes'], backup=change.get('backup'))
        save(root, plan_id, record)
    return status(root, plan_id)


def project_pr(root, plan_id, *, apply=False):
    from plane_workflow import run, configuration_lock
    root, record = read(root, plan_id)
    if not apply:
        return {'plan_id': plan_id, 'status': 'planned', 'next_step': 'project_pr', 'writes_performed': False}
    require(record.get('project') and record['project']['status'] == 'diff_prepared', 'Prepare the isolated project diff first.')
    project, spec = record['project'], record['plan']
    tracked_install = spec['channel'] == 'skills' and spec['installation'].get('tracked_project_installation')
    if not spec['project_plan']['changes'] and not tracked_install:
        return status(root, plan_id)
    require(not tracked_install or record['local'] in ('project_installation_staged', 'verified'),
            'Refresh tracked project skills in the isolated upgrade workspace before preparing its PR.')
    workspace = Path(project['path'])
    require(run(['git', 'branch', '--show-current'], workspace).stdout.strip() == project['branch'], 'Upgrade checkout branch changed.')
    planned = set(spec['project_plan']['changes'])
    changed = set(run(['git', 'diff', '--name-only', spec['base_sha']], workspace).stdout.splitlines())
    staged = set(run(['git', 'diff', '--cached', '--name-only', spec['base_sha']], workspace).stdout.splitlines())
    untracked = run(['git', 'ls-files', '--others', '--exclude-standard'], workspace).stdout.splitlines()
    def owned(path):
        if path in planned:
            return True
        if not tracked_install:
            return False
        if path == 'skills-lock.json':
            return True
        return any(path == folder + '/' + name or path.startswith(folder + '/' + name + '/')
                   for folder in ('.agents/skills', '.codex/skills', '.claude/skills', '.cursor/skills', '.config/opencode/skills') for name in SKILLS)
    require(all(owned(path) for path in changed | staged | set(untracked)), 'Upgrade workspace contains unrelated changes.')
    for name, change in spec['project_plan']['changes'].items():
        path = workspace / name
        matches = (not path.exists() and not path.is_symlink()) if change['after'] == 'missing' else (
            path.is_file() and not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest() == change['after'])
        require(matches, 'Planned project files changed after preparation; preserve modifications and review again.')
    if tracked_install:
        require(all(inventory(workspace / '.agents/skills' / name) == expected_payload(spec['target'], 'skills/' + name)
                    for name in SKILLS), 'Tracked skill payload changed after preparation; preserve it and review again.')
    planned |= changed | staged | set(untracked)
    from shared_sync import workflow, WORKFLOW
    if spec['project_plan']['provider'] == 'actions':
        require((workspace / WORKFLOW).read_text() == workflow(spec['target']['commit'], spec['target']['version']), 'Upgrade workflow changed after review.')
    if tracked_install:
        verify_project_lock(spec['installation'], workspace, allow_product_changes=True)
    marker = f'<!-- plane-devflow:product-upgrade:{plan_id} -->'
    args = ['gh', 'pr', 'list', '--repo', spec['repository'], '--head', project['branch'], '--base', spec['base'],
            '--state', 'all', '--json', 'url,body,state,headRefOid']
    existing = json.loads(run(args, workspace).stdout)
    require(len(existing) <= 1 and all(marker in item.get('body', '') for item in existing), 'Conflicting upgrade PR; reconcile before creating.')
    if existing:
        require(existing[0]['state'] in ('OPEN', 'MERGED'), 'The existing upgrade PR was closed; inspect its outcome before retrying.')
        require(existing[0]['headRefOid'] == run(['git', 'rev-parse', 'HEAD'], workspace).stdout.strip(), 'Existing upgrade PR has a different head.')
        url = existing[0]['url']
    else:
        if run(['git', 'status', '--porcelain'], workspace).stdout.strip():
            run(['git', 'add', '--', *sorted(planned)], workspace)
            run(['git', '-c', 'core.hooksPath=/dev/null', 'commit', '-m', f'Upgrade Plane DevFlow to {spec["target"]["version"]}'], workspace)
        run(['git', 'push', '-u', 'origin', project['branch']], workspace)
        body = f'Upgrade Plane DevFlow to {spec["target"]["tag"]} ({spec["target"]["commit"]}).\n\nPreserves project mapping, credentials and task policy. Connection verification follows activation.\n\n{marker}\n'
        with tempfile.TemporaryDirectory(prefix='plane-upgrade-pr-') as temporary:
            body_path = Path(temporary) / 'body.md'
            body_path.write_text(body)
            url = run(['gh', 'pr', 'create', '--repo', spec['repository'], '--base', spec['base'], '--head', project['branch'],
                       '--title', f'Upgrade Plane DevFlow to {spec["target"]["version"]}', '--body-file', str(body_path)], workspace).stdout.strip()
    import re
    require(re.fullmatch(r'https://github\.com/' + re.escape(spec['repository']) + r'/pull/[0-9]+', url), 'Unexpected upgrade PR URL.')
    with configuration_lock(root):
        root, record = read(root, plan_id)
        record['pr'] = url
        record['project']['commit'] = run(['git', 'rev-parse', 'HEAD'], workspace).stdout.strip()
        save(root, plan_id, record)
    return status(root, plan_id)


def tracked_payload_deployed(root, spec, revision):
    """A local refresh cannot stand in for tracked files on the activation branch."""
    from plane_sync import WorkflowError
    if spec['channel'] != 'skills' or not spec['installation'].get('tracked_project_installation'):
        return True
    try:
        return all(baseline_files(root, spec['target']['version'], '.agents/skills/' + name,
                                  dict(spec['target'], commit=revision)) == expected_payload(spec['target'], 'skills/' + name)
                   for name in SKILLS)
    except (ValueError, subprocess.CalledProcessError, WorkflowError):
        return False


def verify_project(root, plan_id):
    """Explicit live reads, with no connection workflow dispatch or Plane writes."""
    from datetime import datetime, timezone
    from plane_workflow import run, configuration_lock
    from github_setup import check
    root, record = read(root, plan_id)
    require(remote_default(root)['branch'] == record['plan']['base'], 'Remote default branch changed; refresh the upgrade plan.')
    run(['git', 'fetch', '--', 'origin', record['plan']['base']], root)
    result = check(root, release_refresh=True)
    native = sync_provider(json.loads((root / CONFIG_NAME).read_text())) == 'native'
    bundle = result.get('sync_bundle', {})
    target = record['plan']['target']
    matches = native or (bundle.get('installed_version') == target['version'] and bundle.get('source_commit') == target['commit'])
    default_sha = run(['git', 'rev-parse', f'origin/{record["plan"]["base"]}'], root).stdout.strip()
    matches = matches and tracked_payload_deployed(root, record['plan'], default_sha)
    identity_verified = native or (bundle.get('integrity_verified') is True and bundle.get('compatible') is True and
                                   result.get('evidence', {}).get('default_sha') == default_sha)
    verified = (matches and identity_verified and result.get('configuration_status') == 'complete' and
                result['checks'].get('native_mapping_verified' if native else 'connection_verified') is True)
    with configuration_lock(root):
        root, record = read(root, plan_id)
        record['verification'] = ({'default_sha': default_sha,
                                   'observed_at': datetime.now(timezone.utc).isoformat(),
                                   'connection_run': result.get('evidence', {}).get('connection_run')}
                                  if verified else None)
        save(root, plan_id, record)
    output = status(root, plan_id)
    output['verification_report'] = result
    output['verification_steps'] = {
        'local_installation': output['local_installation'],
        'project_activated': output['project_activated'],
        'release_identity_verified': identity_verified,
        'connection_verified': result['checks'].get('native_mapping_verified' if native else 'connection_verified'),
        'overall_verified': verified}
    return output


def rollback(root, plan_id, *, apply=False):
    """Prepare a scoped reverse diff, including tracked project skill files."""
    from plane_workflow import run, configuration_lock
    root, record = read(root, plan_id)
    project, spec = record.get('project'), record['plan']
    require(project and project.get('branch'), 'No isolated project upgrade is available for rollback.')
    commit = project.get('commit') or run(['git', 'rev-parse', project['branch']], root).stdout.strip()
    changed = run(['git', 'diff', '--name-only', spec['base_sha'], commit], root).stdout.splitlines()
    require(changed, 'The upgrade has no committed project changes; preserve or discard its unmerged isolated diff explicitly.')
    tracked = spec['channel'] == 'skills' and spec['installation'].get('tracked_project_installation')
    def owned(path):
        return path in spec['project_plan']['changes'] or (tracked and (path == 'skills-lock.json' or any(
            path == folder + '/' + name or path.startswith(folder + '/' + name + '/')
            for folder in ('.agents/skills', '.codex/skills', '.claude/skills', '.cursor/skills', '.config/opencode/skills') for name in SKILLS)))
    require(all(owned(path) for path in changed), 'Upgrade history includes unrelated changes; review rollback manually.')
    result = {'plan_id': plan_id, 'status': 'rollback_planned', 'files': changed,
              'local_downgrade': 'Use the original channel after the project rollback is active; never downgrade alone.',
              'writes_performed': False}
    if not apply:
        return result
    with configuration_lock(root):
        root, record = read(root, plan_id)
        require(remote_default(root)['branch'] == spec['base'], 'Remote default branch changed; review rollback against its actual activation branch.')
        run(['git', 'fetch', '--', 'origin', spec['base']], root)
        current = run(['git', 'rev-parse', f'origin/{spec["base"]}'], root).stdout.strip()
        require(run(['git', 'show', f'{current}:{CONFIG_NAME}'], root).stdout ==
                run(['git', 'show', f'{spec["base_sha"]}:{CONFIG_NAME}'], root).stdout,
                'Project mapping changed; preserve it and review rollback.')
        for name in changed:
            require(run(['git', 'ls-tree', current, '--', name], root).stdout ==
                    run(['git', 'ls-tree', commit, '--', name], root).stdout,
                    'Current project files differ from the deployed upgrade; preserve later changes and review rollback.')
        directory, _ = paths(root, plan_id)
        workspace = directory / 'rollback'
        branch = 'codex/plane-devflow-rollback-' + plan_id[:8]
        if not record.get('rollback_workspace'):
            record['rollback_workspace'] = str(workspace)
            record['rollback'] = {'branch': branch, 'base_sha': current, 'status': 'preparing'}
            save(root, plan_id, record)
        require(record['rollback']['base_sha'] == current,
                'Default branch moved during rollback preparation; preserve its diff and review again.')
        ensure_worktree(root, workspace, branch, current)
        require(not run(['git', 'diff', '--cached', '--name-only', current], workspace).stdout.strip(),
                'Rollback checkout has staged changes; preserve them for review.')
        modified = set(run(['git', 'diff', '--name-only', current], workspace).stdout.splitlines())
        untracked = set(run(['git', 'ls-files', '--others', '--exclude-standard'], workspace).stdout.splitlines())
        require(modified | untracked <= set(changed), 'Rollback checkout contains unrelated changes.')
        def blob(revision, name):
            entry = git(root, 'ls-tree', revision, '--', name)
            return None if not entry else (entry.split()[0], git(root, 'show', f'{revision}:{name}'))
        def contents(path):
            if path.is_symlink():
                return b'120000', os.fsencode(os.readlink(path))
            if path.is_file():
                return b'file', path.read_bytes()
            require(not path.exists(), 'Rollback file was replaced by a directory; preserve it for review.')
            return None
        def comparable(entry):
            return (b'120000' if entry[0] == b'120000' else b'file', entry[1]) if entry else None
        desired = {name: comparable(blob(spec['base_sha'], name)) for name in changed}
        for name in changed:
            found = contents(workspace / name)
            allowed = (desired[name],) if record['rollback']['status'] == 'diff_prepared' else (
                desired[name], comparable(blob(current, name)))
            require(found in allowed, 'Rollback files changed after preparation; preserve modifications for review.')
        if record['rollback']['status'] != 'diff_prepared':
            run(['git', 'restore', '--source', spec['base_sha'], '--worktree', '--', *changed], workspace)
            require(all(contents(workspace / name) == desired[name] for name in changed), 'Rollback restoration is incomplete; resume preparation.')
            record['rollback']['status'] = 'diff_prepared'
            save(root, plan_id, record)
        result.update(workspace=str(workspace), branch=branch, writes_performed=True,
                      next_step='Review the reverse diff and prepare a separate rollback PR; do not reset the default branch.')
    return result


def install_local(root, plan_id, *, apply=False):
    if not apply:
        return _install_local(root, plan_id, apply=False)
    root, record = read(root, plan_id)
    if record['plan']['channel'] == 'plugin':
        return _install_local(root, plan_id, apply=True)
    lock = Path(record['plan']['installation']['target']).parent / '.plane-devflow-install.lock'
    require(not lock.parent.is_symlink(), 'Installation lock must stay in the selected installation scope.')
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = lock.open('x')
    except FileExistsError:
        raise ValueError('Another installation update owns this scope; preserve its lock and inspect before retrying.') from None
    try:
        with handle:
            handle.write(str(os.getpid()) + '\n')
        return _install_local(root, plan_id, apply=True)
    finally:
        lock.unlink()


def _install_local(root, plan_id, *, apply=False):
    from plane_workflow import configuration_lock
    root, record = read(root, plan_id)
    if not apply:
        return {'plan_id': plan_id, 'status': 'planned', 'next_step': 'install_local', 'writes_performed': False}
    require(record['source'] and record['project'], 'Stage the source and prepare the project diff before changing the installation.')
    if record['plan']['channel'] == 'skills':
        verify_installer_environment(record['plan']['installation'])
    verify_source(record['source'], record['plan']['target'], allow_candidate=record['plan'].get('candidate_source', False))
    if record['plan']['channel'] == 'plugin':
        return {'plan_id': plan_id, 'status': 'local_refresh_pending', 'next_step': 'Update through the original plugin channel, reopen the session, and verify the installed version.'}
    spec = record['plan']
    selected = spec['installation']
    target = Path(selected['target'])
    tracked = selected.get('tracked_project_installation')
    install_root, install_target = root, target
    if tracked:
        from plane_workflow import run
        from shared_sync import identity, WORKFLOW
        require(record['project'].get('path'), 'Tracked project skills need an isolated project checkout.')
        install_root = Path(record['project']['path'])
        install_target = install_root / '.agents/skills'
        require(run(['git', 'branch', '--show-current'], install_root).stdout.strip() == record['project']['branch'],
                'Upgrade checkout changed branches; preserve it before refreshing tracked skills.')
        if record['local'] == 'project_installation_staged':
            require(remote_default(root)['branch'] == spec['base'], 'Remote default branch changed; preserve the original checkout and replan.')
            run(['git', 'fetch', '--', 'origin', spec['base']], root)
            deployed = run(['git', 'show', f'origin/{spec["base"]}:{WORKFLOW}'], root, check=False)
            found = identity(deployed.stdout.encode()) if deployed.returncode == 0 else None
            native_ready = False
            if spec['project_plan']['provider'] == 'native':
                try:
                    native_ready = all(
                        baseline_files(root, spec['target']['version'], '.agents/skills/' + name,
                                       dict(spec['target'], commit=run(['git', 'rev-parse', f'origin/{spec["base"]}'], root).stdout.strip()))
                        == expected_payload(spec['target'], 'skills/' + name) for name in SKILLS)
                except (ValueError, subprocess.CalledProcessError):
                    native_ready = False
            if native_ready or found == {'version': spec['target']['version'], 'commit': spec['target']['commit']}:
                require(run(['git', 'branch', '--show-current'], root).stdout.strip() == spec['base'] and
                        not run(['git', 'status', '--porcelain', '--', '.', ':(exclude).agents/.plane-devflow-install.lock'], root).stdout.strip(),
                        'Project update is merged; synchronize the original checkout without overwriting user work, then resume installation verification.')
                run(['git', 'merge', '--ff-only', f'origin/{spec["base"]}'], root)
                install_root, install_target = root, target
    if selected['scope'] == 'project':
        verify_project_lock(selected, install_root,
                            allow_product_changes=record['local'] in ('installing', 'project_installation_staged', 'verified'))
    else:
        verify_global_lock(selected, allow_product_changes=record['local'] in ('installing', 'verified'))
    current = {name: inventory(target / name) for name in SKILLS}
    expected = {name: inventory(Path(record['source']) / 'skills' / name) for name in SKILLS}
    original_hosts = verify_host_entries(selected, target.parent.parent, target, expected,
                                         resumed=record['local'] in ('installing', 'project_installation_staged', 'verified'))
    if current == expected and host_refresh_complete(selected, original_hosts, expected):
        with configuration_lock(root):
            root, record = read(root, plan_id)
            record['local'] = 'verified'
            save(root, plan_id, record)
        return status(root, plan_id)
    if tracked:
        workspace_hosts = verify_host_entries(selected, install_root, install_target, expected,
                                              resumed=record['local'] in ('installing', 'project_installation_staged', 'verified'))
        current = {name: inventory(install_target / name) for name in SKILLS}
        if current == expected and host_refresh_complete(selected, workspace_hosts, expected):
            with configuration_lock(root):
                root, record = read(root, plan_id)
                record['local'] = 'verified' if install_target == target else 'project_installation_staged'
                save(root, plan_id, record)
            return status(root, plan_id)
    interrupted = record['local'] == 'installing'
    if interrupted:
        for name in SKILLS:
            before, after, found = selected['before'][name] or {}, expected[name], current[name] or {}
            require(all(value in (before.get(path), after.get(path)) for path, value in found.items()) and
                    set(found) <= set(before) | set(after), 'Partial installation contains unknown changes; preserve them for review.')
    else:
        require(current == selected['before'], 'Installed skill files changed since review; preserve modifications and plan again.')
    # Keep a payload-only backup for explicit rollback, not credentials or host config.
    directory, _ = paths(root, plan_id)
    backup = directory / 'installation-before'
    if not backup.exists():
        backup.mkdir()
    for name in SKILLS:
        original = selected['before'][name]
        if original is not None and not (backup / name).exists():
            require(current[name] == original, 'Interrupted backup requires review before installation continues.')
            with tempfile.TemporaryDirectory(prefix='.backup-stage-', dir=backup) as temporary:
                staged = Path(temporary) / name
                shutil.copytree(install_target / name, staged)
                require(inventory(staged) == original, 'Installation changed while preparing its backup.')
                staged.rename(backup / name)
        require(inventory(backup / name) == original, 'Installation backup differs from the reviewed original.')
    with configuration_lock(root):
        root, record = read(root, plan_id)
        record.update(local='installing', installation_backup=str(backup))
        save(root, plan_id, record)
    source = f'https://github.com/{REPOSITORY}/tree/{spec["target"]["commit"]}'
    if record.get('candidate_source'):
        source = record['source']
    args = ['npx', '--yes', 'skills@1.7.4', 'add', source, '--skill', *SKILLS,
            '--agent', selected['host'], '--yes']
    if selected['scope'] == 'global':
        args.append('--global')
    result = run_installer(args, install_root)
    require(result.returncode == 0, 'Skills installation failed; inspect installed files and resume from the saved plan.')
    if selected['scope'] == 'project':
        preserve_lock_metadata(selected, install_root)
    else:
        verify_global_lock(selected, allow_product_changes=True)
    require({name: inventory(install_target / name) for name in SKILLS} == expected, 'Installed payload differs from the selected release.')
    installed_hosts = verify_host_entries(selected, install_root if tracked or selected['scope'] == 'project' else target.parent.parent,
                                          install_target, expected, resumed=True)
    require(host_refresh_complete(selected, installed_hosts, expected), 'Selected host installation differs from the selected release.')
    with configuration_lock(root):
        root, record = read(root, plan_id)
        record['local'] = 'project_installation_staged' if tracked and install_target != target else 'verified'
        record['installation_backup'] = str(backup)
        save(root, plan_id, record)
    return status(root, plan_id)


def confirm_plugin(root, plan_id, *, plugin_root=None, apply=False):
    from plane_workflow import configuration_lock
    root, record = read(root, plan_id)
    require(record['plan']['channel'] == 'plugin' and record['source'], 'Expected a staged plugin upgrade.')
    verify_source(record['source'], record['plan']['target'], allow_candidate=record['plan'].get('candidate_source', False))
    expected = expected_payload(record['plan']['target'], 'plugins/plane-devflow')
    # Native hosts may activate a new versioned cache directory rather than
    # overwrite the original source. Explicitly inspect that active path without
    # changing the original plan or converting installation channels.
    active = Path(plugin_root or record.get('confirmed_plugin_root') or record['plan']['installation']['target']).resolve()
    metadata = active / 'plugin.json'
    require(metadata.is_file() and not metadata.is_symlink() and
            hashlib.sha256(metadata.read_bytes()).hexdigest() == expected['plugin.json'],
            'Active plugin installation does not match the selected product payload.')
    actual = inventory(active)
    require(actual == expected, 'Active plugin installation does not match the selected product payload.')
    if apply:
        with configuration_lock(root):
            root, record = read(root, plan_id)
            record['local'] = 'verified'
            record['confirmed_plugin_root'] = str(active)
            save(root, plan_id, record)
    return status(root, plan_id)


def status(root, plan_id):
    from plane_workflow import run
    from shared_sync import identity
    root, record = read(root, plan_id)
    spec = record['plan']
    target = spec['target']
    local = record['local']
    if spec['channel'] == 'skills' and local == 'verified':
        selected = spec['installation']
        if not record['source'] or any(inventory(Path(selected['target']) / name) != expected_payload(target, 'skills/' + name) for name in SKILLS):
            local = 'changed_after_verification'
        if local == 'verified':
            expected = {name: expected_payload(target, 'skills/' + name) for name in SKILLS}
            try:
                entries = verify_host_entries(selected, Path(selected['target']).parent.parent,
                                              selected['target'], expected, resumed=True)
                if not host_refresh_complete(selected, entries, expected):
                    local = 'changed_after_verification'
            except (ValueError, OSError, WorkflowError):
                local = 'changed_after_verification'
    elif spec['channel'] == 'plugin' and local == 'verified':
        if not record['source'] or inventory(record.get('confirmed_plugin_root') or spec['installation']['target']) != expected_payload(target, 'plugins/plane-devflow'):
            local = 'changed_after_verification'
    remote = None
    if record['project'] and spec['project_plan']['provider'] == 'native':
        activated = True
    else:
        result = run(['git', 'show', f'origin/{spec["base"]}:.github/workflows/plane-devflow.yml'], root, check=False)
        remote = identity(result.stdout.encode()) if result.returncode == 0 else None
        activated = remote == {'version': target['version'], 'commit': target['commit']}
    activated = activated and tracked_payload_deployed(root, spec, 'origin/' + spec['base'])
    verification = record.get('verification')
    from github_setup import freshness
    age = freshness(verification.get('observed_at')) if verification else 'unknown'
    verified = bool(verification and age == 'fresh' and verification.get('default_sha') == run(['git', 'rev-parse', f'origin/{spec["base"]}'], root).stdout.strip())
    if local == 'verified' and activated and verified:
        state = 'candidate_complete' if record.get('candidate_source') else 'complete'
    elif activated:
        state = 'verification_pending' if local == 'verified' else 'local_refresh_pending'
    elif record.get('pr'):
        state = 'activation_pending'
    elif record['project']:
        state = 'project_pr_pending'
    else:
        state = 'staged' if record['source'] else 'planned'
    return {'plan_id': plan_id, 'status': state, 'target_version': target['version'], 'target_commit': target['commit'],
            'local_installation': local, 'project': record['project'], 'pr': record.get('pr'),
            'project_activated': activated, 'activation_source': 'local_remote_tracking_ref_not_live',
            'connection_verified': verified, 'verification_freshness': age, 'event_writeback_verified': None,
            'validation_mode': 'candidate_fixture' if record.get('candidate_source') else 'stable_release',
            'record_path': str(paths(root, plan_id)[1])}
