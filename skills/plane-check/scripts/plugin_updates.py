"""Anonymous, advisory GitHub release discovery; no installation or persistent state."""
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

RELEASE_API = 'https://api.github.com/repos/SoaringLabs/plane-devflow/releases/latest'
LATEST_RELEASE_PAGE = 'https://github.com/SoaringLabs/plane-devflow/releases/latest'
RELEASE_PAGE = 'https://github.com/SoaringLabs/plane-devflow/releases/tag/'
CHECK_TIMEOUT = 3
MAX_RESPONSE_BYTES = 128 * 1024
ERRORS = {'network_unavailable', 'rate_limited_or_forbidden', 'release_unavailable',
          'upstream_unavailable', 'invalid_response'}


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', value):
        raise ValueError('Unsupported stable version.')
    return tuple(map(int, value.split('.')))


def release_metadata(data):
    if not isinstance(data, dict) or data.get('draft') is not False or data.get('prerelease') is not False:
        raise ValueError('Expected a stable release.')
    tag = data.get('tag_name')
    if not isinstance(tag, str):
        raise ValueError('Missing release tag.')
    version = tag.removeprefix('v')
    version_tuple(version)
    if data.get('html_url') != RELEASE_PAGE + tag:
        raise ValueError('Unexpected release source.')
    return {key: data[key] for key in ('tag_name', 'html_url', 'draft', 'prerelease')}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def release_link(opener):
    """On API quota failure, inspect the canonical latest link without following it."""
    request = Request(LATEST_RELEASE_PAGE, method='HEAD', headers={'User-Agent': 'plane-devflow-update-check'})
    try:
        with opener.open(request, timeout=2):
            return None  # A page without a release redirect proves no version.
    except HTTPError as error:
        location = error.headers.get('Location', '')
        if error.code not in {301, 302, 303, 307, 308} or not location.startswith(RELEASE_PAGE):
            return None
        try:
            return release_metadata({'tag_name': location[len(RELEASE_PAGE):], 'html_url': location,
                                     'draft': False, 'prerelease': False})
        except (ValueError, TypeError):
            return None
    except (OSError, URLError):
        return None


def fetch_release():
    """Fixed public metadata only; at most one quota fallback within the worker deadline."""
    request = Request(RELEASE_API, headers={'Accept': 'application/vnd.github+json',
                                          'User-Agent': 'plane-devflow-update-check'})
    opener = build_opener(NoRedirect())
    try:
        with opener.open(request, timeout=2) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError('Release response too large.')
        return release_metadata(json.loads(body.decode('utf-8')))
    except HTTPError as error:
        if error.code in {403, 429}:
            fallback = release_link(opener)
            if fallback is not None:
                return fallback
        reason = ('rate_limited_or_forbidden' if error.code in {403, 429} else
                  'release_unavailable' if error.code == 404 else 'upstream_unavailable')
        return {'error': reason}
    except (OSError, URLError):
        return {'error': 'network_unavailable'}
    except (ValueError, TypeError, RecursionError):
        return {'error': 'invalid_response'}


def check_updates(*, offline=False):
    from plugin_version import VERSION
    result = {'installed_version': VERSION, 'latest_version': None, 'status': 'unverified',
              'update_available': None, 'release_url': None, 'notice': None,
              'blocking': False, 'source': 'github_latest_stable_release', 'reason': 'offline' if offline else None}
    if offline:
        return result
    try:
        # A process deadline also bounds DNS and slow responses, unlike a socket timeout alone.
        worker = subprocess.run([sys.executable, '-I', str(Path(__file__).resolve()), '--fetch'],
                                stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                timeout=CHECK_TIMEOUT)
        if worker.returncode != 0:
            result['reason'] = 'check_failed'
            return result
        data = json.loads(worker.stdout)
        if isinstance(data, dict) and data.get('error') in ERRORS:
            result['reason'] = data['error']
            return result
        metadata = release_metadata(data)
        latest = metadata['tag_name'].removeprefix('v')
        remote, installed = version_tuple(latest), version_tuple(VERSION)
        newer = remote > installed
        result.update(latest_version=latest, release_url=metadata['html_url'], update_available=newer,
                      status='update_available' if newer else 'ahead' if remote < installed else 'current')
        if newer:
            result['notice'] = (f'Plane DevFlow {latest} 已发布（当前 {VERSION}）：{metadata["html_url"]}。'
                                '此检查仅报告版本；更新安装需单独授权。')
    except subprocess.TimeoutExpired:
        result['reason'] = 'timeout'
    except OSError:
        result['reason'] = 'check_failed'
    except (ValueError, TypeError, RecursionError):
        result['reason'] = 'invalid_response'
    return result


if __name__ == '__main__' and sys.argv[1:] == ['--fetch']:
    print(json.dumps(fetch_release()))
