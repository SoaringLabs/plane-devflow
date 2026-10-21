"""Synthetic vaults only: these tests never load the user's native credential store."""
import contextlib
import ctypes
import io
import json
import subprocess
import unittest
from unittest.mock import MagicMock, patch

import test_github_setup as fixtures
import credential_store as vault
import plane_workflow as workflow
import plane_sync as sync

TOKEN = "synthetic-pat-never-a-real-credential"
ACCOUNT = "user@example.test"


class ScopeTests(unittest.TestCase):
    def test_reuses_across_repositories_and_projects_but_separates_account_workspace_instance(self):
        config = fixtures.config()
        scope = vault.Scope.from_config(config, ACCOUNT)
        other = fixtures.config()
        other['github']['repository'] = 'different-owner/new-repo'
        other['plane']['project_id'] = 'another-project'
        self.assertEqual(scope.key, vault.Scope.from_config(other, ACCOUNT.upper()).key)
        other['plane']['api_url'] = config['plane']['api_url'].upper() + '/'
        self.assertEqual(scope.key, vault.Scope.from_config(other, ACCOUNT).key)
        for section, key, value in [('plane','workspace','second-workspace'),
                                     ('plane','api_url','https://other.example.test')]:
            changed = fixtures.config()
            changed[section][key] = value
            self.assertNotEqual(scope.key, vault.Scope.from_config(changed, ACCOUNT).key)
        self.assertNotEqual(scope.key, vault.Scope.from_config(config, 'someone-else@example.test').key)

    def test_lookup_never_loads_secret_and_unavailable_is_unknown(self):
        store = MagicMock()
        store.contains.return_value = True
        with patch.object(vault, 'open_store', return_value=store):
            result = vault.inspect(fixtures.config(), ACCOUNT)
        store.read.assert_not_called()
        self.assertTrue(result['saved'])
        self.assertEqual(result['credential_validity'], 'unverified')
        with patch.object(vault, 'open_store', side_effect=vault.VaultError('locked')):
            result = vault.inspect(fixtures.config(), ACCOUNT)
        self.assertIsNone(result['saved'])
        self.assertEqual(result['status'], 'unavailable')

    def test_unsupported_platform_never_loads_native_libraries_or_writes_files(self):
        with patch.object(vault.sys, 'platform', 'linux'), patch.object(ctypes, 'CDLL') as loader:
            result = vault.inspect(fixtures.config(), ACCOUNT)
        loader.assert_not_called()
        self.assertEqual(result['status'], 'unavailable')
        self.assertIsNone(result['backend'])

    def test_invalid_account_and_token_are_not_echoed_in_errors(self):
        for account in [None, '', 'bad\naccount']:
            with self.assertRaises(sync.WorkflowError):
                vault.Scope.from_config(fixtures.config(), account)
        for token in ['', TOKEN+'\n', TOKEN+'\x00', 'x'*2561]:
            with self.assertRaises(sync.WorkflowError) as caught:
                vault.validate_token(token)
            self.assertNotIn(TOKEN, str(caught.exception))


class WindowsAdapterTests(unittest.TestCase):
    def setUp(self):
        self.scope = vault.Scope.from_config(fixtures.config(), ACCOUNT)
        self.api = MagicMock()
        self.rows = []
        self.stored = TOKEN
        self.last_error = 1168
        def read(target, kind, flags, output):
            self.assertEqual((target, kind, flags), (self.scope.key, 1, 0))
            if self.stored is None:
                return 0
            raw = self.stored.encode()
            buffer = ctypes.create_string_buffer(raw)
            row = vault.Credential(Type=1, CredentialBlobSize=len(raw),
                                   CredentialBlob=ctypes.cast(buffer, ctypes.c_void_p))
            pointer = ctypes.pointer(row)
            self.rows.append((row, buffer, pointer))
            ctypes.cast(output, ctypes.POINTER(ctypes.POINTER(vault.Credential)))[0] = pointer
            return 1
        def write(pointer, flags):
            row = ctypes.cast(pointer, ctypes.POINTER(vault.Credential)).contents
            self.assertEqual((row.Type, row.Persist, row.TargetName), (1, 2, self.scope.key))
            self.stored = ctypes.string_at(row.CredentialBlob, row.CredentialBlobSize).decode()
            return 1
        self.api.CredReadW.side_effect = read
        self.api.CredWriteW.side_effect = write
        self.api.CredDeleteW.return_value = 1
        self.loader = patch.object(ctypes, 'WinDLL', create=True, return_value=self.api)
        self.loader.start()
        self.addCleanup(self.loader.stop)
        self.errors = patch.object(ctypes, 'get_last_error', create=True, side_effect=lambda: self.last_error)
        self.errors.start()
        self.addCleanup(self.errors.stop)
        self.store = vault.WindowsCredentials(self.scope)

    def test_read_and_presence_free_and_wipe_native_buffers(self):
        self.assertTrue(self.store.contains())
        self.assertEqual(self.store.read(), TOKEN)
        self.assertEqual(self.api.CredFree.call_count, 2)
        for row, buffer, pointer in self.rows:
            self.assertEqual(buffer.raw, b'\0'*len(buffer))

    def test_save_refuses_implicit_replacement_and_writes_generic_local_credential(self):
        with self.assertRaisesRegex(sync.WorkflowError, 'already saved'):
            self.store.save(TOKEN)
        self.api.CredWriteW.assert_not_called()
        self.store.save('replacement-synthetic', replace=True)
        self.assertEqual(self.stored, 'replacement-synthetic')

    def test_not_found_differs_from_denial(self):
        self.stored = None
        self.assertFalse(self.store.contains())
        self.last_error = 5
        with self.assertRaises(vault.VaultError):
            self.store.contains()

    def test_delete_only_targets_selected_entry_and_is_idempotent(self):
        self.store.delete()
        self.api.CredDeleteW.assert_called_once_with(self.scope.key, 1, 0)
        self.api.CredDeleteW.return_value = 0
        self.store.delete()  # ERROR_NOT_FOUND
        self.last_error = 5
        with self.assertRaises(vault.VaultError):
            self.store.delete()


class MacAdapterTests(unittest.TestCase):
    def setUp(self):
        # Mock the native libraries before construction; never touch Keychain.
        self.cf, self.sec = MagicMock(), MagicMock()
        with patch.object(ctypes, 'CDLL', side_effect=[self.cf, self.sec]) as loader:
            self.store = vault.MacKeychain(vault.Scope.from_config(fixtures.config(), ACCOUNT))
        self.assertEqual(loader.call_count, 2)
        self.queries = []
        @contextlib.contextmanager
        def attributes(extra=(), token=None):
            self.queries.append((extra, token))
            yield 101
        self.store.attributes = attributes
        self.store.constant = lambda key: key
        self.raw = ctypes.create_string_buffer(TOKEN.encode())
        self.cf.CFDataGetLength.return_value = len(TOKEN)
        self.cf.CFDataGetBytePtr.return_value = ctypes.addressof(self.raw)
        def copy(query, result):
            ctypes.cast(result, ctypes.POINTER(ctypes.c_void_p))[0] = 202
            return 0
        self.sec.SecItemCopyMatching.side_effect = copy

    def test_status_requests_attributes_with_no_unlock_and_read_requests_data(self):
        self.assertTrue(self.store.contains())
        self.cf.CFDataGetBytePtr.assert_not_called()
        self.assertIn(('kSecUseAuthenticationUI', 'kSecUseAuthenticationUIFail'), self.queries[0][0])
        self.assertEqual(self.store.read(), TOKEN)
        self.assertEqual(self.queries[1][0], [('kSecReturnData','kCFBooleanTrue')])
        self.assertEqual(self.cf.CFRelease.call_count, 2)

    def test_missing_locked_and_duplicate_are_distinct(self):
        self.sec.SecItemCopyMatching.side_effect = None
        self.sec.SecItemCopyMatching.return_value = -25300
        self.assertFalse(self.store.contains())
        self.sec.SecItemCopyMatching.return_value = -25308
        with self.assertRaises(vault.VaultError):
            self.store.contains()
        self.sec.SecItemAdd.return_value = -25299
        with self.assertRaisesRegex(sync.WorkflowError, 'already saved'):
            self.store.save(TOKEN)
        self.sec.SecItemUpdate.assert_not_called()
        self.sec.SecItemUpdate.return_value = 0
        self.store.save(TOKEN, replace=True)
        self.sec.SecItemUpdate.assert_called_once()

    def test_null_success_result_does_not_dereference_data(self):
        self.sec.SecItemCopyMatching.side_effect = None
        self.sec.SecItemCopyMatching.return_value = 0
        with self.assertRaises(vault.VaultError):
            self.store.read()
        self.cf.CFDataGetLength.assert_not_called()

    def test_native_dictionary_uses_data_payload_and_releases_owned_references(self):
        self.store.attributes = vault.MacKeychain.attributes.__get__(self.store)
        self.cf.CFDictionaryCreateMutable.return_value = 101
        self.cf.CFStringCreateWithCString.side_effect = [301,302]
        copied = []
        def copy_data(allocator, buffer, size):
            copied.append(ctypes.string_at(buffer, size))
            return 303
        self.cf.CFDataCreate.side_effect = copy_data
        self.sec.SecItemAdd.return_value = 0
        self.store.save(TOKEN)
        self.assertEqual(copied, [TOKEN.encode()])
        pairs = {call.args[1]:call.args[2] for call in self.cf.CFDictionarySetValue.call_args_list}
        self.assertEqual(pairs, {'kSecClass':'kSecClassGenericPassword', 'kSecAttrService':301,
                                 'kSecAttrAccount':302, 'kSecValueData':303})
        self.assertEqual([call.args[0] for call in self.cf.CFRelease.call_args_list], [101,303,302,301])
        # The transient write buffer passed to CFDataCreate is cleared, and no
        # command-line executable is used to store the token.
        buffer = self.cf.CFDataCreate.call_args.args[1]
        self.assertEqual(buffer.raw, b'\0'*len(buffer))


class CredentialCommandTests(unittest.TestCase):
    setUp = fixtures.RepositoryTests.setUp

    def fake_store(self):
        store = MagicMock()
        store.contains.return_value = False
        store.read.return_value = TOKEN
        return store

    def test_plan_and_noninteractive_mutations_never_open_vault(self):
        with patch.object(vault, 'open_store') as store, patch.object(workflow.sys.stdin, 'isatty', return_value=False):
            for action in ['remember','forget']:
                plan = workflow.local_credential(self.root, action=action, account=ACCOUNT)
                self.assertFalse(plan['writes_performed'])
                with self.assertRaises(sync.WorkflowError):
                    workflow.local_credential(self.root, action=action, account=ACCOUNT, apply=True)
            with self.assertRaises(sync.WorkflowError):
                workflow.set_secret(self.root, account=ACCOUNT, use_saved=True)
        store.assert_not_called()

    def test_remember_is_opt_in_hidden_input_and_not_a_repository_file(self):
        store = self.fake_store()
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*') if '.git' not in p.parts)
        with patch.object(vault, 'open_store', return_value=store), patch.object(workflow.sys.stdin, 'isatty', return_value=True), \
             patch.object(workflow.getpass, 'getpass', return_value=TOKEN):
            result = workflow.local_credential(self.root, action='remember', account=ACCOUNT, apply=True)
        store.save.assert_called_once_with(TOKEN, replace=False)
        self.assertNotIn(TOKEN, json.dumps(result))
        self.assertEqual(before, sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*') if '.git' not in p.parts))

    def test_use_saved_sends_only_stdin_after_target_confirmation(self):
        store = self.fake_store()
        real_run = workflow.run
        calls = []
        def fake_run(args, *pos, **kw):
            if args[0] == 'gh':
                calls.append((args,kw))
                return subprocess.CompletedProcess(args, 0, '[]', '')
            return real_run(args, *pos, **kw)
        with patch.object(vault, 'open_store', return_value=store), patch.object(workflow.sys.stdin, 'isatty', return_value=True), \
             patch('builtins.input', return_value='example/demo-project'), patch.object(workflow, 'run', side_effect=fake_run), \
             patch.object(workflow.getpass, 'getpass', side_effect=AssertionError('saved flow needs no PAT prompt')):
            result = workflow.set_secret(self.root, account=ACCOUNT, use_saved=True)
        self.assertEqual(calls[-1][0], ['gh','secret','set','PLANE_API_KEY','--repo','example/demo-project'])
        self.assertEqual(calls[-1][1]['input_text'], TOKEN)
        self.assertNotIn(TOKEN, json.dumps(result))
        self.assertTrue(all(TOKEN not in ' '.join(call[0]) for call in calls))
        store.save.assert_not_called()

    def test_cancellation_and_existing_remote_secret_load_no_credentials(self):
        for present, confirmation in [(False,'wrong/repository'), (True,'example/demo-project')]:
            with self.subTest(present=present), patch.object(workflow, 'credential_guide', return_value={'secret_present':present}), \
                 patch.object(vault, 'open_store') as store, patch.object(workflow.sys.stdin, 'isatty', return_value=True), \
                 patch('builtins.input', return_value=confirmation):
                with self.assertRaises(sync.WorkflowError):
                    workflow.set_secret(self.root, account=ACCOUNT, use_saved=True)
                store.assert_not_called()

    def test_hidden_input_unavailable_does_not_fall_back_to_echo(self):
        with patch.object(workflow.getpass, 'getpass', side_effect=workflow.getpass.GetPassWarning('unsafe')):
            with self.assertRaisesRegex(sync.WorkflowError, 'Hidden input unavailable'):
                workflow.hidden_pat('hidden')

    def test_confirmation_eof_and_interrupt_cancel_before_loading_a_token(self):
        for cancellation in [EOFError, KeyboardInterrupt]:
            with self.subTest(cancellation=cancellation), patch.object(workflow, 'credential_guide', return_value={'secret_present':False}), \
                 patch.object(vault, 'open_store') as store, patch.object(workflow.sys.stdin, 'isatty', return_value=True), \
                 patch('builtins.input', side_effect=cancellation):
                with self.assertRaisesRegex(sync.WorkflowError, 'Cancelled'):
                    workflow.set_secret(self.root, account=ACCOUNT, use_saved=True)
                store.assert_not_called()

    def test_mapping_changed_during_hidden_input_does_not_save_under_old_scope(self):
        store = self.fake_store()
        def enter(prompt):
            config = fixtures.config()
            config['plane']['workspace'] = 'different-workspace'
            (self.root / sync.CONFIG_NAME).write_text(json.dumps(config))
            return TOKEN
        with patch.object(vault, 'open_store', return_value=store), patch.object(workflow.sys.stdin, 'isatty', return_value=True), \
             patch.object(workflow.getpass, 'getpass', side_effect=enter):
            with self.assertRaisesRegex(sync.WorkflowError, 'mapping changed'):
                workflow.local_credential(self.root, action='remember', account=ACCOUNT, apply=True)
        store.save.assert_not_called()

    def test_decode_errors_never_reveal_credential_bytes(self):
        store = self.fake_store()
        store.read.side_effect = UnicodeDecodeError('utf-8', TOKEN.encode(), 0, 1, 'invalid')
        with patch.object(workflow, 'credential_guide', return_value={'secret_present':False}), \
             patch.object(vault, 'open_store', return_value=store), patch.object(workflow.sys.stdin, 'isatty', return_value=True), \
             patch('builtins.input', return_value='example/demo-project'):
            with self.assertRaises(sync.WorkflowError) as caught:
                workflow.set_secret(self.root, account=ACCOUNT, use_saved=True)
        self.assertNotIn(TOKEN, str(caught.exception))

    def test_forget_never_revokes_plane_or_deletes_github_secret(self):
        store = self.fake_store()
        with patch.object(vault, 'open_store', return_value=store), patch.object(workflow.sys.stdin, 'isatty', return_value=True), \
             patch('builtins.input', return_value=ACCOUNT):
            result = workflow.local_credential(self.root, action='forget', account=ACCOUNT, apply=True)
        store.delete.assert_called_once()
        store.read.assert_not_called()
        self.assertEqual(result['status'], 'forgotten')

    def test_native_skips_all_saved_pat_routes(self):
        config = fixtures.config()
        config['sync'] = {'provider':'native'}
        (self.root / sync.CONFIG_NAME).write_text(json.dumps(config))
        with patch.object(vault, 'open_store') as store:
            self.assertEqual(workflow.credential_guide(self.root, step='local', account=ACCOUNT)['status'], 'skipped')
            with self.assertRaises(sync.WorkflowError):
                workflow.local_credential(self.root, account=ACCOUNT)
        store.assert_not_called()

    def test_local_guide_requires_account_then_offers_saved_value_without_returning_it(self):
        with patch.object(vault, 'open_store') as opener:
            result = workflow.credential_guide(self.root)
        opener.assert_not_called()
        self.assertEqual(result['next_step'], 'select_plane_account')
        store = self.fake_store()
        store.contains.return_value = True
        with patch.object(vault, 'open_store', return_value=store):
            result = workflow.credential_guide(self.root, account=ACCOUNT)
        self.assertEqual(result['next_step'], 'confirm_saved_credential')
        store.read.assert_not_called()

    def test_no_cli_token_argument(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit):
                workflow.main(['set-secret','--token'])

    def test_unavailable_vault_routes_to_unlock_or_manual_instead_of_missing(self):
        with patch.object(vault, 'open_store', side_effect=vault.VaultError('locked')):
            result = workflow.credential_guide(self.root, account=ACCOUNT)
        self.assertEqual(result['next_step'], 'unlock_storage_or_manual')
        self.assertIsNone(result['local_credential']['saved'])

    def test_remote_metadata_failure_stops_before_loading_vault(self):
        with patch.object(workflow, 'credential_guide', side_effect=sync.WorkflowError('permission unknown')), \
             patch.object(vault, 'open_store') as store, patch.object(workflow.sys.stdin, 'isatty', return_value=True):
            with self.assertRaises(sync.WorkflowError):
                workflow.set_secret(self.root, account=ACCOUNT, use_saved=True)
        store.assert_not_called()

    def test_secret_created_during_confirmation_is_not_overwritten(self):
        store = self.fake_store()
        with patch.object(workflow, 'credential_guide', side_effect=[{'secret_present':False}, {'secret_present':True}]), \
             patch.object(vault, 'open_store', return_value=store), patch.object(workflow.sys.stdin, 'isatty', return_value=True), \
             patch('builtins.input', return_value='example/demo-project'), patch.object(workflow, 'run', wraps=workflow.run) as run:
            with self.assertRaisesRegex(sync.WorkflowError, 'Secret changed'):
                workflow.set_secret(self.root, account=ACCOUNT, use_saved=True)
        self.assertFalse(any(call.args[0][0] == 'gh' for call in run.call_args_list))

    def test_origin_changed_during_confirmation_loads_no_token(self):
        real_run = workflow.run
        def confirm(prompt):
            real_run(['git','remote','set-url','origin','https://github.com/other/repo.git'], self.root)
            return 'example/demo-project'
        with patch.object(workflow, 'credential_guide', return_value={'secret_present':False}), \
             patch.object(vault, 'open_store') as store, patch.object(workflow.sys.stdin, 'isatty', return_value=True), \
             patch('builtins.input', side_effect=confirm):
            with self.assertRaisesRegex(sync.WorkflowError, 'origin'):
                workflow.set_secret(self.root, account=ACCOUNT, use_saved=True)
        store.assert_not_called()

    def test_manual_route_does_not_persist_and_partial_upload_keeps_opted_in_local_entry(self):
        for remember in [False,True]:
            store = self.fake_store()
            real_run = workflow.run
            def fail_upload(args, *pos, **kw):
                if args[0] == 'gh':
                    raise sync.WorkflowError('upload uncertain')
                return real_run(args, *pos, **kw)
            with self.subTest(remember=remember), patch.object(workflow, 'credential_guide', return_value={'secret_present':False}), \
                 patch.object(vault, 'open_store', return_value=store) as opener, patch.object(workflow.sys.stdin, 'isatty', return_value=True), \
                 patch('builtins.input', return_value='example/demo-project'), patch.object(workflow.getpass, 'getpass', return_value=TOKEN), \
                 patch.object(workflow, 'run', side_effect=fail_upload):
                with self.assertRaises(sync.WorkflowError) as caught:
                    workflow.set_secret(self.root, account=ACCOUNT, remember=remember)
            store.delete.assert_not_called()
            self.assertNotIn(TOKEN, str(caught.exception))
            if remember:
                store.save.assert_called_once_with(TOKEN, replace=False)
                self.assertIn('retained', str(caught.exception))
            else:
                opener.assert_not_called()
