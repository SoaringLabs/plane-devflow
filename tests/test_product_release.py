"""Release identity cache never substitutes for explicit live acceptance."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_product_upgrade import release_fixture
import product_release as releases
import release_cache as cache
from setup_errors import ProbeError


class ReleaseCacheTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        environment = patch.dict(os.environ, {'XDG_CACHE_HOME': str(Path(self.temporary.name).resolve())})
        environment.start()
        self.addCleanup(environment.stop)
        self.manifest = release_fixture()
        self.metadata = {'draft': False, 'prerelease': False, 'tag_name': 'v0.14.0', 'assets': [
            {'name': 'plane-devflow-release.json', 'id': 123,
             'browser_download_url': 'https://github.com/SoaringLabs/plane-devflow/releases/download/v0.14.0/plane-devflow-release.json'}]}

    def remote(self, *, metadata=None, manifest=None):
        return (patch.object(releases, 'fetch_json', side_effect=[metadata or self.metadata,
                    {'object': {'type': 'tag', 'sha': 'c' * 40}},
                    {'object': {'type': 'commit', 'sha': 'a' * 40}}]),
                patch.object(releases, 'fetch_asset', return_value=manifest or self.manifest))

    def test_repeated_fixed_release_checks_share_one_validated_identity(self):
        metadata, asset = self.remote()
        with metadata as calls, asset as downloads:
            observed, cached = {}, {}
            first = releases.resolve('0.14.0', observation=observed)
            second = releases.resolve('0.14.0', observation=cached)
        self.assertEqual(first, second)
        self.assertEqual(observed['source'], 'github_release')
        self.assertEqual(cached['source'], 'verified_release_cache')
        self.assertEqual(calls.call_count, 3)  # No redundant asset-metadata GET.
        self.assertEqual(downloads.call_count, 1)
        record = cache.read('identity-0.14.0')
        self.assertEqual(record['asset_id'], 123)
        self.assertEqual(record['manifest_sha256'], cache.digest(first))
        # A separate process/module has no in-memory state to depend on.
        self.assertEqual(cache.load_identity('0.14.0'), first)
        self.assertIsNone(cache.load_identity('0.14.1'))

    def test_explicit_refresh_rechecks_a_moved_tag_instead_of_accepting_cache(self):
        cache.save_identity(self.manifest, 123)
        with patch.object(releases, 'fetch_json', side_effect=[self.metadata, {'object': {'type': 'commit', 'sha': 'd' * 40}}]), patch.object(releases, 'fetch_asset', return_value=self.manifest), self.assertRaisesRegex(ValueError, 'identity mismatch'):
            releases.resolve('0.14.0', refresh=True)

    def test_explicit_refresh_and_latest_never_fall_back_to_cached_success(self):
        cache.save_identity(self.manifest, 123)
        for version, refresh in [('0.14.0', True), (None, False)]:
            with self.subTest(version=version), patch.object(releases, 'fetch_json', side_effect=ProbeError('rate_limited', 'product_release')) as request:
                with self.assertRaises(ProbeError):
                    releases.resolve(version, refresh=refresh)
                request.assert_called_once()

    def test_expired_future_and_modified_cache_require_live_reads(self):
        cache.save_identity(self.manifest, 123)
        original = cache.read('identity-0.14.0')
        changes = [dict(observed_at=0), dict(observed_at=10**12), dict(commit='d' * 40),
                   dict(manifest_sha256='0' * 64), dict(version='0.14.1'), dict(asset_id=True),
                   dict(manifest={'channel': 'candidate'})]
        for change in changes:
            with self.subTest(change=change):
                cache.write('identity-0.14.0', dict(original, **change))
                self.assertIsNone(cache.load_identity('0.14.0'))
                metadata, asset = self.remote()
                with metadata as calls, asset:
                    self.assertEqual(releases.resolve('0.14.0'), self.manifest)
                self.assertEqual(calls.call_count, 3)

    def test_invalid_and_candidate_releases_never_enter_cache(self):
        wrong = copy.deepcopy(self.manifest)
        wrong['commit'] = 'd' * 40
        candidate = copy.deepcopy(self.manifest)
        candidate['channel'] = 'candidate'
        for manifest in (wrong, candidate):
            metadata, asset = self.remote(manifest=manifest)
            with metadata, asset, self.assertRaises(ValueError):
                releases.resolve('0.14.0')
            self.assertIsNone(cache.read('identity-0.14.0'))

    def test_noncanonical_download_and_duplicate_assets_are_rejected(self):
        for url in ('https://evil.invalid/manifest.json', 'https://github.com/other/repo/releases/download/v0.14.0/plane-devflow-release.json'):
            data = copy.deepcopy(self.metadata)
            data['assets'][0]['browser_download_url'] = url
            metadata, asset = self.remote(metadata=data)
            with metadata, asset as download, self.assertRaises(ValueError):
                releases.resolve('0.14.0')
            download.assert_not_called()
        data = copy.deepcopy(self.metadata)
        data['assets'] *= 2
        metadata, asset = self.remote(metadata=data)
        with metadata, asset, self.assertRaises(ValueError):
            releases.resolve('0.14.0')

    def test_corrupt_unwritable_and_symlink_cache_do_not_block_live_resolution(self):
        base = cache.directory()
        base.mkdir(parents=True)
        path = base / 'identity-0.14.0.json'
        path.write_text('broken json')
        metadata, asset = self.remote()
        with metadata, asset, patch.object(cache.os, 'replace', side_effect=PermissionError):
            self.assertEqual(releases.resolve('0.14.0'), self.manifest)
        self.assertEqual(path.read_text(), 'broken json')
        self.assertEqual(list(base.iterdir()), [path])
        target = Path(self.temporary.name) / 'user-file'
        target.write_text('preserve')
        path.unlink()
        try:
            path.symlink_to(target)
        except OSError:
            self.skipTest('Creating symlinks requires platform support.')
        metadata, asset = self.remote()
        with metadata, asset:
            self.assertEqual(releases.resolve('0.14.0'), self.manifest)
        self.assertEqual(target.read_text(), 'preserve')

    def test_asset_redirects_are_public_https_only_without_authorization(self):
        from urllib.request import Request
        def inspect_opener(handler):
            request = Request('https://github.com/SoaringLabs/plane-devflow/releases/download/v0.14.0/plane-devflow-release.json')
            safe = handler.redirect_request(request, None, 302, 'Found', {}, 'https://release-assets.githubusercontent.com/asset')
            self.assertNotIn('Authorization', safe.headers)
            for url in ('http://release-assets.githubusercontent.com/asset', 'https://evil.invalid/asset',
                        'https://user:pass@github.com/asset', 'https://github.com:444/asset'):
                with self.assertRaises(ValueError):
                    handler.redirect_request(request, None, 302, 'Found', {}, url)
            raise OSError('stop before network')
        with patch.object(releases, 'build_opener', side_effect=inspect_opener), self.assertRaises(OSError):
            releases.fetch_asset('https://github.com/SoaringLabs/plane-devflow/releases/download/v0.14.0/plane-devflow-release.json')


if __name__ == '__main__':
    unittest.main()
