"""Best-effort, per-user public release metadata. Never cache project readiness."""
import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

MAX_BYTES = 8 * 1024 * 1024
IDENTITY_TTL = 60 * 60


def directory():
    base = Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache')
    if not base.is_absolute():
        return None
    return base / 'plane-devflow' / 'releases'


def safe(path):
    return not any(part.is_symlink() for part in (path, *path.parents))


def read(name):
    base = directory()
    if base is None:
        return None
    path = base / (name + '.json')
    try:
        if not safe(path) or path.stat().st_size > MAX_BYTES:
            return None
        return json.loads(path.read_bytes())
    except (OSError, ValueError, RecursionError):
        return None


def write(name, value):
    base = directory()
    if base is None:
        return
    temporary = None
    try:
        if not safe(base):
            return
        base.mkdir(parents=True, exist_ok=True, mode=0o700)
        destination = base / (name + '.json')
        if not safe(destination):
            return
        payload = json.dumps(value, sort_keys=True).encode()
        if len(payload) > MAX_BYTES:
            return
        with tempfile.NamedTemporaryFile(dir=base, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
        os.replace(temporary, destination)
    except OSError:
        pass  # An unavailable cache must not prevent a live verification.
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def digest(manifest):
    return hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()


def load_identity(version, *, observation=None):
    from product_release import REPOSITORY, validate_manifest
    value = read('identity-' + version)
    try:
        if (not isinstance(value, dict) or value.get('schema') != 1 or
                value.get('repository') != REPOSITORY or value.get('version') != version or
                type(value.get('observed_at')) not in (int, float) or
                not 0 <= time.time() - value['observed_at'] < IDENTITY_TTL or
                type(value.get('asset_id')) is not int or value['asset_id'] <= 0):
            return None
        manifest = validate_manifest(value['manifest'])
        if (manifest['version'] != version or manifest['commit'] != value['commit'] or
                digest(manifest) != value['manifest_sha256']):
            return None
        if observation is not None:
            observation.update(source='verified_release_cache', observed_at=value['observed_at'])
        return manifest
    except (KeyError, ValueError, TypeError):
        return None


def save_identity(manifest, asset_id):
    write('identity-' + manifest['version'], {
        'schema': 1, 'repository': manifest['repository'], 'version': manifest['version'],
        'commit': manifest['commit'], 'asset_id': asset_id, 'manifest_sha256': digest(manifest),
        'observed_at': time.time(), 'manifest': manifest})


def cooldown(mode):
    value = read('cooldown-' + mode)
    if isinstance(value, dict) and type(value.get('retry_at')) is int and value['retry_at'] > time.time():
        try:
            datetime.fromtimestamp(value['retry_at'], timezone.utc)
            return value['retry_at']
        except (ValueError, OverflowError, OSError):
            pass
    return None
