"""Credential-free transport fixtures for authentication, quotas and safe errors."""
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from contextlib import redirect_stderr, redirect_stdout
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugins/plane-devflow/scripts'))
import release_cache as cache
import release_transport as transport
from setup_errors import ProbeError

URL = transport.API_PREFIX + 'releases/tags/v0.14.0'


def response(status=200, headers='', body=b'{"tag_name":"v0.14.0"}'):
    content = f'HTTP/2.0 {status} Status\r\n{headers}\r\n\r\n'.encode() + body
    return subprocess.CompletedProcess(['gh'], int(status != 200), content, b'private diagnostic never echoed')


class ReleaseTransportTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        environment = patch.dict(os.environ, {'XDG_CACHE_HOME': str(Path(temporary.name).resolve())}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    def test_existing_gh_session_is_used_for_fixed_host_without_token_extraction(self):
        with patch.object(transport.shutil, 'which', return_value='/fixture/gh'), patch.object(transport.subprocess, 'run', return_value=response()) as run, patch.object(transport, 'build_opener') as anonymous:
            self.assertEqual(transport.fetch_json(URL)['tag_name'], 'v0.14.0')
        args = run.call_args.args[0]
        self.assertEqual(args, ['gh', 'api', '--hostname', 'github.com', '--include', 'repos/SoaringLabs/plane-devflow/releases/tags/v0.14.0'])
        self.assertNotIn('GH_DEBUG', run.call_args.kwargs['env'])
        self.assertEqual(run.call_args.kwargs['timeout'], 10)
        anonymous.assert_not_called()

    def test_unconfigured_or_missing_gh_uses_unauthenticated_public_get(self):
        empty = subprocess.CompletedProcess(['gh'], 1, b'', b'To get started with GitHub CLI, please run: gh auth login')
        for which in (None, '/fixture/gh'):
            with self.subTest(which=which), patch.object(transport.shutil, 'which', return_value=which), patch.object(transport.subprocess, 'run', return_value=empty), patch.object(transport, 'build_opener') as opener:
                opener.return_value.open.return_value.__enter__.return_value.read.return_value = b'{"public":true}'
                self.assertEqual(transport.fetch_json(URL), {'public': True})
                request = opener.return_value.open.call_args.args[0]
                self.assertEqual(request.full_url, URL)
                self.assertFalse(request.has_header('Authorization'))

    def test_authentication_permission_and_not_found_errors_do_not_change_identity(self):
        for status, code in ((401, 'authentication_required'), (403, 'permission_denied'), (404, 'not_found_or_hidden')):
            with self.subTest(status=status), patch.object(transport.subprocess, 'run', return_value=response(status)), patch.object(transport.shutil, 'which', return_value='gh'), patch.object(transport, 'build_opener') as anonymous:
                with self.assertRaises(ProbeError) as caught:
                    transport.fetch_json(URL)
                self.assertEqual(caught.exception.issue['code'], code)
                self.assertNotIn('private diagnostic', str(caught.exception))
                anonymous.assert_not_called()

    def test_primary_limit_returns_reset_time_and_suppresses_repeated_requests(self):
        headers = 'X-RateLimit-Remaining: 0\r\nX-RateLimit-Reset: 4600'
        with patch.object(transport.time, 'time', return_value=1000), patch.object(transport.subprocess, 'run', return_value=response(403, headers)) as run:
            for _ in range(2):
                with self.assertRaises(ProbeError) as caught:
                    transport.gh_json(URL)
                self.assertEqual(caught.exception.issue['code'], 'rate_limited')
                self.assertEqual(caught.exception.issue['stage'], 'product_release')
                self.assertEqual(caught.exception.issue['retry_at'], datetime.fromtimestamp(4600, timezone.utc).isoformat())
            self.assertEqual(run.call_count, 1)
        with patch.object(transport.time, 'time', return_value=4601), patch.object(transport.subprocess, 'run', return_value=response()):
            self.assertEqual(transport.gh_json(URL)['tag_name'], 'v0.14.0')

    def test_retry_after_and_malformed_headers_remain_bounded_and_structured(self):
        for status, headers, expected in (
                (429, {'Retry-After': '120'}, 1120),
                (403, {'Retry-After': 'Thu, 01 Jan 1970 00:20:00 GMT'}, 1200),
                (429, {}, 1060),
                (403, {'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset': 'invalid'}, 1060)):
            with self.subTest(headers=headers), patch.object(transport.time, 'time', return_value=1000):
                error = transport.response_error(status, headers, 'gh')
                self.assertEqual(error.issue['code'], 'rate_limited')
                self.assertEqual(cache.cooldown('gh'), expected)

    def test_anonymous_limit_uses_separate_cooldown_and_never_echoes_response_body(self):
        error = HTTPError(URL, 403, 'Forbidden', {'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset': '4600'}, io.BytesIO(b'sensitive fixture response'))
        with patch.object(transport.time, 'time', return_value=1000), patch.object(transport.shutil, 'which', return_value=None), patch.object(transport, 'build_opener') as opener:
            opener.return_value.open.side_effect = error
            for _ in range(2):
                with self.assertRaises(ProbeError) as caught:
                    transport.fetch_json(URL)
                self.assertNotIn('sensitive fixture', str(caught.exception))
            self.assertEqual(opener.return_value.open.call_count, 1)
            self.assertIsNone(cache.cooldown('gh'))

    def test_secondary_limit_with_remaining_quota_is_not_a_permission_error(self):
        with patch.object(transport.time, 'time', return_value=1000), patch.object(transport.subprocess, 'run', return_value=response(403, 'X-RateLimit-Remaining: 50', b'{"message":"You have exceeded a secondary rate limit"}')):
            with self.assertRaises(ProbeError) as caught:
                transport.gh_json(URL)
        self.assertEqual(caught.exception.issue['code'], 'rate_limited')
        self.assertEqual(caught.exception.issue['retry_at'], datetime.fromtimestamp(1060, timezone.utc).isoformat())

    def test_timeout_invalid_json_and_large_bodies_do_not_expose_diagnostics(self):
        for result, code in ((response(body=b'private invalid json'), 'invalid_response'),
                             (response(body=b'x' * (transport.MAX_BYTES + 1)), 'invalid_response'),
                             (subprocess.CompletedProcess(['gh'], 1, b'', b'private network error'), 'network_unavailable')):
            with self.subTest(code=code), patch.object(transport.subprocess, 'run', return_value=result), self.assertRaises(ProbeError) as caught:
                transport.gh_json(URL)
            self.assertEqual(caught.exception.issue['code'], code)
            self.assertNotIn('private', str(caught.exception))
        with patch.object(transport.subprocess, 'run', side_effect=subprocess.TimeoutExpired(['gh'], 10)), self.assertRaises(ProbeError) as caught:
            transport.gh_json(URL)
        self.assertEqual(caught.exception.issue['code'], 'network_unavailable')

    def test_untrusted_api_endpoints_are_rejected_before_cli_or_http(self):
        for url in ('https://evil.invalid/releases/latest', 'http://api.github.com/repos/SoaringLabs/plane-devflow/releases/latest', URL + '?redirect=1'):
            with self.subTest(url=url), patch.object(transport.subprocess, 'run') as run, patch.object(transport, 'build_opener') as opener, self.assertRaises(ProbeError):
                transport.fetch_json(url)
            run.assert_not_called()
            opener.assert_not_called()

    def test_explicit_cli_resolution_bypasses_cache_and_reports_safe_structured_failure(self):
        import product_release
        import plane_workflow
        error = transport.rate_error(4600)
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(product_release, 'resolve', side_effect=error) as resolve, redirect_stdout(stdout), redirect_stderr(stderr):
            code = plane_workflow.main(['resolve-release', '--target-version', '0.14.0'])
        self.assertEqual(code, 1)
        resolve.assert_called_once_with('0.14.0', refresh=True)
        data = json.loads(stdout.getvalue())
        self.assertEqual(data['status'], 'unverified')
        self.assertEqual(data['issue'], error.issue)
        self.assertIn('Retry at', stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
