"""One product release identity, validated before installation or project changes."""
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path, PurePosixPath
from urllib.request import Request, build_opener

from release_transport import fetch_json
import release_cache

from plugin_version import VERSION

REPOSITORY = 'SoaringLabs/plane-devflow'
SKILLS = ('plane-setup', 'plane-start', 'plane-deliver')
SHA = re.compile(r'[0-9a-f]{40}')
SEMVER = re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)')


def require(value, message):
    if not value:
        raise ValueError(message)


def git(root, *args):
    result = subprocess.run(['git', *args], cwd=root, capture_output=True, check=True)
    return result.stdout


def validate_manifest(data, *, allow_candidate=False):
    require(isinstance(data, dict) and data.get('schema') == 1, 'Unsupported release manifest.')
    require(data.get('repository') == REPOSITORY, 'Unexpected release repository.')
    require(isinstance(data.get('version'), str) and SEMVER.fullmatch(data['version']), 'Invalid product version.')
    require(data.get('tag') == 'v' + data['version'], 'Release tag/version mismatch.')
    require(isinstance(data.get('commit'), str) and SHA.fullmatch(data['commit']), 'Expected a full release commit.')
    require(data.get('channel') == 'stable' or (allow_candidate and data.get('channel') == 'candidate'), 'A formal stable release is required.')
    require(data.get('skills') == list(SKILLS), 'Unexpected public skill inventory.')
    require(data.get('config_versions') == [1, 2] and data.get('binding_versions') == [1], 'Unsupported release contracts.')
    files = data.get('files')
    require(isinstance(files, dict) and bool(files), 'Missing release fingerprints.')
    for name, digest in files.items():
        require(isinstance(name, str) and name and '\\' not in name and not PurePosixPath(name).is_absolute()
                and all(part not in ('', '.', '..', '.git') for part in name.split('/')), 'Unsafe release path.')
        require(isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest), 'Invalid release fingerprint.')
    required = ['VERSION', 'action.yml', 'plugins/plane-devflow/plugin.json',
                *[f'plugins/plane-devflow/scripts/{name}.py' for name in
                  ('plugin_version', 'plane_workflow', 'plane_sync', 'action_runner', 'product_release', 'product_upgrade', 'shared_sync')],
                *[f'skills/{name}/{file}' for name in SKILLS for file in ('distribution.json', 'SKILL.md')]]
    require(all(name in files for name in required), 'Incomplete release payload.')
    return data


def manifest(root, commit, *, candidate=False):
    """Read committed bytes only; the manifest is an external release asset."""
    require(SHA.fullmatch(commit), 'Expected a full source commit.')
    version = git(root, 'show', f'{commit}:VERSION').decode().strip()
    files = {}
    for raw in git(root, 'ls-tree', '-rz', '--full-tree', commit).split(b'\0'):
        if not raw:
            continue
        info, name = raw.split(b'\t', 1)
        mode, kind, oid = info.split()
        require(mode in (b'100644', b'100755') and kind == b'blob', 'Release payload contains a symlink or submodule.')
        files[name.decode()] = hashlib.sha256(git(root, 'cat-file', 'blob', oid.decode())).hexdigest()
    return validate_manifest({'schema': 1, 'repository': REPOSITORY, 'version': version, 'tag': 'v' + version,
                             'commit': commit, 'channel': 'candidate' if candidate else 'stable', 'skills': list(SKILLS),
                             'config_versions': [1, 2], 'binding_versions': [1], 'files': files}, allow_candidate=candidate)


def verify_source(root, release, *, allow_candidate=False):
    release = validate_manifest(release, allow_candidate=allow_candidate)
    root = Path(root).resolve()
    actual = set()
    for path in root.rglob('*'):
        relative = path.relative_to(root)
        if relative.parts[0] == '.git' or '__pycache__' in relative.parts:
            continue
        require(not path.is_symlink(), 'Symlink in staged release.')
        if path.is_file():
            actual.add(relative.as_posix())
    require(actual == set(release['files']), 'Unexpected or missing staged release files.')
    for name, expected in release['files'].items():
        path = root / name
        require(not any(parent.is_symlink() for parent in (path, *path.parents) if parent == root or root in parent.parents),
                'Symlink in staged release.')
        require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected, f'Release payload mismatch: {name}')
    require((root / 'VERSION').read_text().strip() == release['version'], 'Product version mismatch.')
    plugin = json.loads((root / 'plugins/plane-devflow/plugin.json').read_text())
    require(plugin['version'] == release['version'], 'Plugin version mismatch.')
    for name in SKILLS:
        require(json.loads((root / f'skills/{name}/distribution.json').read_text())['version'] == release['version'],
                'Standalone version mismatch.')
    return release


def fetch_asset(url):
    from urllib.parse import urlsplit
    from urllib.request import HTTPRedirectHandler
    allowed = ('github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com')

    class PublicAssetRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            parsed = urlsplit(newurl)
            require(parsed.scheme == 'https' and parsed.hostname in allowed and not parsed.username and not parsed.password
                    and parsed.port in (None, 443), 'Unexpected release asset redirect.')
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    with build_opener(PublicAssetRedirect()).open(Request(url, headers={'User-Agent': 'plane-devflow-release'}), timeout=3) as response:
        content = response.read(4 * 1024 * 1024 + 1)
    require(len(content) <= 4 * 1024 * 1024, 'Release manifest too large.')
    return json.loads(content)


def resolve(version=None, *, refresh=False, observation=None):
    """Resolve an official release; explicit selection/acceptance bypasses identity cache."""
    if version is not None:
        require(SEMVER.fullmatch(version), 'Expected a stable product version.')
        if not refresh:
            cached = release_cache.load_identity(version, observation=observation)
            if cached is not None:
                return cached
    endpoint = 'latest' if version is None else 'tags/v' + version
    data = fetch_json(f'https://api.github.com/repos/{REPOSITORY}/releases/{endpoint}')
    require(data.get('draft') is False and data.get('prerelease') is False, 'Expected a published stable release.')
    tag = data.get('tag_name', '')
    require(tag.startswith('v') and SEMVER.fullmatch(tag[1:]), 'Invalid published release tag.')
    require(version is None or tag == 'v' + version, 'Unexpected target release.')
    # Resolve annotated tags recursively, instead of trusting target_commitish.
    ref = fetch_json(f'https://api.github.com/repos/{REPOSITORY}/git/ref/tags/{tag}')['object']
    for _ in range(5):
        if ref.get('type') == 'commit':
            break
        require(ref.get('type') == 'tag' and SHA.fullmatch(ref.get('sha', '')), 'Invalid release tag object.')
        ref = fetch_json(f'https://api.github.com/repos/{REPOSITORY}/git/tags/{ref["sha"]}')['object']
    require(ref.get('type') == 'commit' and SHA.fullmatch(ref.get('sha', '')), 'Cannot resolve release commit.')
    # Release metadata already contains the asset identity and download source.
    assets = [asset for asset in data.get('assets', []) if asset.get('name') == 'plane-devflow-release.json']
    require(len(assets) == 1, 'Release has no unique product manifest; legacy release needs an explicit migration path.')
    asset_id = assets[0].get('id')
    require(type(asset_id) is int and asset_id > 0, 'Invalid manifest asset.')
    download = assets[0].get('browser_download_url')
    expected = f'https://github.com/{REPOSITORY}/releases/download/{tag}/plane-devflow-release.json'
    require(download == expected, 'Unexpected manifest download source.')
    release = validate_manifest(fetch_asset(download))
    require(release['tag'] == tag and release['commit'] == ref['sha'], 'Manifest/tag identity mismatch.')
    release_cache.save_identity(release, asset_id)
    if observation is not None:
        observation.update(source='github_release', observed_at=time.time())
    return release
