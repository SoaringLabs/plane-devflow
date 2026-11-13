"""Canonical public release reads using existing gh authentication when available."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import os
import re
import shutil
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import Request, build_opener

import release_cache
from setup_errors import ProbeError

MAX_BYTES = 4 * 1024 * 1024
API_PREFIX = 'https://api.github.com/repos/SoaringLabs/plane-devflow/'


def rate_error(retry_at):
    error = ProbeError('rate_limited', 'product_release')
    error.issue['retry_at'] = datetime.fromtimestamp(retry_at, timezone.utc).isoformat()
    error.args = (str(error) + ' Retry at ' + error.issue['retry_at'] + '.',)
    return error


def response_error(status, headers, mode, *, secondary=False):
    headers = {key.lower(): value for key, value in headers.items()}
    limited = status == 429 or (status == 403 and (secondary or
                               headers.get('x-ratelimit-remaining') == '0' or 'retry-after' in headers))
    if limited:
        now = int(time.time())
        deadlines = [now + 60]
        if headers.get('x-ratelimit-remaining') == '0':
            try:
                deadlines.append(int(headers.get('x-ratelimit-reset', '0')))
            except (ValueError, TypeError):
                pass
        try:
            retry = headers.get('retry-after', '')
            if retry:
                deadlines.append(now + int(retry) if retry.isdigit() else
                                 int(parsedate_to_datetime(retry).timestamp()))
        except (ValueError, TypeError, OverflowError, OSError):
            pass
        retry_at = max(deadlines)
        try:
            datetime.fromtimestamp(retry_at, timezone.utc)
        except (ValueError, OverflowError, OSError):
            retry_at = now + 60
        release_cache.write('cooldown-' + mode, {'retry_at': retry_at})
        return rate_error(retry_at)
    code = ('authentication_required' if status == 401 else 'permission_denied' if status == 403 else
            'not_found_or_hidden' if status == 404 else 'network_unavailable' if status >= 500 else 'invalid_response')
    return ProbeError(code, 'product_release')


def decode(content):
    if len(content) > MAX_BYTES:
        raise ProbeError('invalid_response', 'product_release')
    try:
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError()
        return data
    except (ValueError, TypeError, RecursionError):
        raise ProbeError('invalid_response', 'product_release') from None


def gh_json(url):
    retry_at = release_cache.cooldown('gh')
    if retry_at:
        raise rate_error(retry_at)
    env = dict(os.environ)
    for name in ('GH_DEBUG', 'GH_FORCE_TTY'):
        env.pop(name, None)
    try:
        result = subprocess.run(['gh', 'api', '--hostname', 'github.com', '--include',
                                 url.removeprefix('https://api.github.com/')],
                                capture_output=True, timeout=10, env=env)
    except FileNotFoundError:
        return None
    except (OSError, subprocess.TimeoutExpired):
        raise ProbeError('network_unavailable', 'product_release') from None
    # Unconfigured gh makes no API call. Invalid/expired credentials must instead
    # remain an authentication failure, without silently changing identities.
    if not result.stdout and result.returncode:
        diagnostic = result.stderr.lower()
        if b'to get started with github cli' in diagnostic or b'not logged into any github hosts' in diagnostic:
            return None
        if b'401' in diagnostic:
            raise ProbeError('authentication_required', 'product_release')
        if b'403' in diagnostic or b'sso' in diagnostic:
            raise ProbeError('permission_denied', 'product_release')
    raw = result.stdout.replace(b'\r\n', b'\n')
    head, separator, body = raw.partition(b'\n\n')
    match = re.match(rb'HTTP/\S+ ([0-9]{3})\b', head)
    if not separator or not match:
        raise ProbeError('network_unavailable' if result.returncode else 'invalid_response', 'product_release')
    status = int(match[1])
    headers = dict(line.decode('utf-8', errors='replace').split(':', 1)
                   for line in head.split(b'\n')[1:] if b':' in line)
    headers = {key.strip(): value.strip() for key, value in headers.items()}
    if status != 200:
        raise response_error(status, headers, 'gh', secondary=b'rate limit' in body[:MAX_BYTES].lower())
    if result.returncode:
        raise ProbeError('probe_failed', 'product_release')
    return decode(body)


def fetch_json(url):
    # Fixed canonical endpoints only; never forward gh authorization to a CDN.
    if not url.startswith(API_PREFIX) or any(char in url for char in ('?', '#', '\\', '\n', '\r')):
        raise ProbeError('invalid_response', 'product_release')
    if shutil.which('gh'):
        data = gh_json(url)
        if data is not None:
            return data
    retry_at = release_cache.cooldown('anonymous')
    if retry_at:
        raise rate_error(retry_at)
    from plugin_updates import NoRedirect
    request = Request(url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'plane-devflow-release'})
    try:
        with build_opener(NoRedirect()).open(request, timeout=3) as response:
            return decode(response.read(MAX_BYTES + 1))
    except HTTPError as error:
        try:
            secondary = b'rate limit' in error.read(MAX_BYTES + 1).lower()
            problem = response_error(error.code, error.headers, 'anonymous', secondary=secondary)
        finally:
            error.close()
        raise problem from None
    except OSError:
        raise ProbeError('network_unavailable', 'product_release') from None
