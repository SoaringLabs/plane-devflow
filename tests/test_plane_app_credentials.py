"""Synthetic sessions, HTTP responses and vaults; never load real credentials."""
import contextlib
from datetime import datetime, timedelta, timezone
import io
import gc
import json
import os
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch
import urllib.error
import uuid
import warnings

import test_github_setup as fixtures
import plane_app_credentials as app
import plane_workflow as workflow
from credential_store import VaultError

TOKEN = "plane_api_synthetic_credential_never_real"
COOKIE = "synthetic-session-cookie-never-real"
ACCOUNT = "synthetic@example.test"
PAT_ID = "99999999-9999-4999-8999-999999999999"


class Store:
    def __init__(self, scope, rows, failures):
        self.scope, self.rows, self.failures = scope, rows, failures

    def contains(self):
        return self.scope.key in self.rows

    def read(self, *, interactive=True):
        if interactive:
            raise AssertionError("Automatic reads must not open native dialogs")
        return self.rows[self.scope.key]

    def save(self, value, *, replace=False, interactive=True):
        if interactive:
            raise AssertionError("Automatic writes must not open native dialogs")
        pending = ":pending:" in self.scope.key
        if self.failures.get("pending" if pending else "target"):
            raise VaultError(TOKEN + COOKIE)
        if self.contains() and not replace:
            raise VaultError("duplicate")
        self.rows[self.scope.key] = value

    def delete(self, *, interactive=True):
        if interactive:
            raise AssertionError("Automatic cleanup must not open native dialogs")
        if self.failures.get("cleanup"):
            raise VaultError(TOKEN)
        self.rows.pop(self.scope.key, None)


class Client:
    def __init__(self):
        self.created, self.verified = [], []
        self.identity_value = {"id": "88888888-8888-4888-8888-888888888888", "email": ACCOUNT}
        self.create_error = self.verify_error = None
        self.expiry_override = False

    def identity(self):
        return self.identity_value

    def tokens(self):
        return [dict(row) for row in self.created]

    def create(self, label, expiry):
        result = {"id": PAT_ID, "label": label, "expired_at": expiry}
        if self.expiry_override:
            result["expired_at"] = None
        self.created.append(result)
        if self.create_error:
            raise self.create_error
        return {**result, "token": TOKEN}

    def verify(self, token, scope, project_id):
        self.verified.append(token)
        if self.verify_error:
            raise self.verify_error
        if token != TOKEN:
            raise VaultError(TOKEN)


@unittest.skipUnless(os.name == "posix", "The macOS operation lock requires POSIX")
class CreationTests(unittest.TestCase):
    def setUp(self):
        fixtures.RepositoryTests.setUp(self)
        self.rows, self.failures, self.client = {}, {}, Client()
        self.directory = self.root / "support" / "ops"
        @contextlib.contextmanager
        def session():
            yield {"session-id": COOKIE}
        self.session_patch = patch.object(app, "app_session", side_effect=session)
        for patcher in (
            patch.object(app.sys, "platform", "darwin"),
            patch.object(app, "operation_directory", return_value=self.directory),
            patch.object(app, "open_store", side_effect=lambda scope: Store(scope, self.rows, self.failures)),
            patch.object(app, "CloudClient", return_value=self.client), self.session_patch):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        self.plan = app.create(self.root, account=ACCOUNT, expires_at=self.expiry)
        self.args = dict(account=ACCOUNT, expires_at=self.plan["expires_at"],
                         operation_id=self.plan["operation_id"], expected_config_sha256=self.plan["config_sha256"])

    def apply(self, **kwargs):
        return app.create(self.root, **(self.args | kwargs), apply=True)

    def assert_no_leak(self, result):
        encoded = json.dumps(result)
        self.assertNotIn(TOKEN, encoded)
        self.assertNotIn(COOKIE, encoded)
        for path in self.directory.glob("*"):
            if path.is_file():
                self.assertNotIn(TOKEN.encode(), path.read_bytes())
                self.assertNotIn(COOKIE.encode(), path.read_bytes())

    def test_plan_has_no_profile_vault_network_or_disk_access(self):
        with patch.object(app, "open_store", side_effect=AssertionError), \
             patch.object(app, "app_session", side_effect=AssertionError), \
             patch.object(app, "operation_directory", side_effect=AssertionError):
            plan = app.create(self.root, account=ACCOUNT, expires_at=self.expiry)
        self.assertFalse(plan["writes_performed"])
        self.assertFalse(self.directory.exists())
        self.assertIn("--expected-config-sha256", plan["apply_command"])
        self.assertIn("--operation-id", plan["apply_command"])

    def test_create_save_readback_project_check_cleanup_and_idempotency(self):
        result = self.apply()
        self.assertEqual(result["status"], "verified")
        self.assertTrue(result["keychain_saved"] and result["verified"])
        self.assertEqual(self.client.verified, [TOKEN, TOKEN])
        self.assertEqual(len(self.rows), 1)
        self.assertEqual(len(self.client.created), 1)
        self.assertEqual(result["pending_cleanup"], "removed")
        self.assert_no_leak(result)
        again = self.apply()
        self.assertEqual(again["status"], "already_completed")
        self.assertFalse(again["verified"])
        self.assertEqual(len(self.client.created), 1)

    def test_missing_login_and_account_mismatch_create_nothing(self):
        with patch.object(app, "app_session", side_effect=app.CredentialError("login_required")):
            result = self.apply()
        self.assertEqual(result["status"], "login_required")
        self.client.identity_value["email"] = "another@example.test"
        result = self.apply()
        self.assertEqual(result["status"], "account_mismatch")
        self.assertEqual(self.client.created, [])
        self.assertEqual(self.rows, {})

    def test_login_then_resume_same_operation(self):
        with patch.object(app, "app_session", side_effect=app.CredentialError("login_required")):
            self.assertEqual(self.apply()["status"], "login_required")
        self.assertEqual(self.apply()["status"], "verified")
        self.assertEqual(len(self.client.created), 1)

    def test_existing_credential_conflicts_without_loading_session(self):
        self.rows[self.plan["keychain_account"]] = "old-synthetic-token"
        with patch.object(app, "app_session", side_effect=AssertionError):
            result = self.apply()
        self.assertEqual(result["status"], "existing_credential")
        self.assertEqual(self.client.created, [])
        self.assertEqual(self.rows[self.plan["keychain_account"]], "old-synthetic-token")

    def test_replace_preserves_old_value_until_verification_and_resumes_pending(self):
        self.rows[self.plan["keychain_account"]] = "old-synthetic-token"
        self.client.verify_error = app.CredentialError("permission_denied")
        result = self.apply(replace=True)
        self.assertEqual(result["status"], "permission_denied")
        self.assertTrue(result["pending_saved"])
        self.assertEqual(self.rows[self.plan["keychain_account"]], "old-synthetic-token")
        self.client.verify_error = None
        result = self.apply(replace=True)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(self.rows[self.plan["keychain_account"]], TOKEN)
        self.assertEqual(len(self.client.created), 1)
        self.assert_no_leak(result)

    def test_target_save_failure_retains_native_pending_copy_for_retry(self):
        self.failures["target"] = True
        result = self.apply()
        self.assertEqual(result["status"], "keychain_unavailable")
        self.assertTrue(result["pending_saved"])
        self.assertFalse(result["keychain_saved"])
        self.assert_no_leak(result)
        self.failures.clear()
        self.assertEqual(self.apply()["status"], "verified")
        self.assertEqual(len(self.client.created), 1)

    def test_pending_save_failure_reconciles_metadata_without_recreating(self):
        self.failures["pending"] = True
        first = self.apply()
        self.assertEqual(first["status"], "keychain_unavailable")
        self.failures.clear()
        again = self.apply()
        self.assertEqual(again["status"], "created_without_local_copy")
        self.assertEqual(again["pat_id"], PAT_ID)
        self.assertEqual(len(self.client.created), 1)
        self.assert_no_leak(again)

    def test_unknown_post_is_never_replayed_even_when_response_was_lost(self):
        self.client.create_error = app.CredentialError("network_unavailable")
        first = self.apply()
        self.assertEqual(first["status"], "creation_unconfirmed")
        self.client.create_error = None
        self.assertEqual(self.apply()["status"], "created_without_local_copy")
        self.assertEqual(len(self.client.created), 1)

    def test_unknown_post_not_found_is_still_uncertain(self):
        self.client.create_error = app.CredentialError("network_unavailable")
        self.apply()
        self.client.created.clear()
        self.client.create_error = None
        self.assertEqual(self.apply()["status"], "creation_unconfirmed")
        self.assertEqual(self.client.created, [])

    def test_other_operation_cannot_bypass_unfinished_creation(self):
        self.failures["target"] = True
        self.apply()
        self.failures.clear()
        result = self.apply(operation_id=str(uuid.uuid4()))
        self.assertEqual(result["status"], "operation_in_progress")
        self.assertEqual(len(self.client.created), 1)

    def test_mapping_change_invalidates_plan_before_any_session_access(self):
        cfg = fixtures.config()
        cfg["github"]["base_branch"] = "release"
        (self.root / ".plane-devflow.json").write_text(json.dumps(cfg))
        with self.assertRaisesRegex(app.CredentialError, "项目配置"):
            self.apply()
        self.assertEqual(self.client.created, [])

    def test_server_expiry_mismatch_stays_pending_and_never_promotes(self):
        self.client.expiry_override = True
        result = self.apply()
        self.assertNotEqual(result["status"], "verified")
        self.assertTrue(result["pending_saved"])
        self.assertNotIn(self.plan["keychain_account"], self.rows)
        self.assertNotEqual(self.apply()["status"], "verified")

    def test_definite_rejection_is_login_not_an_ambiguous_creation(self):
        self.client.create_error = app.CredentialError("login_required")
        result = self.apply()
        self.assertEqual(result["status"], "login_required")
        # The synthetic server rejected this attempt; a later login can retry.
        self.client.created.clear()
        self.client.create_error = None
        self.assertEqual(self.apply()["status"], "verified")

    def test_expired_verified_pending_operation_does_not_block_a_new_authorization(self):
        self.failures["target"] = True
        self.apply()
        later = datetime.now(timezone.utc) + timedelta(hours=2)
        later_expiry = (later + timedelta(hours=1)).isoformat()
        self.failures.clear()
        with patch.object(app, "utcnow", return_value=later):
            new_plan = app.create(self.root, account=ACCOUNT, expires_at=later_expiry)
            result = self.apply(operation_id=new_plan["operation_id"], expires_at=new_plan["expires_at"])
        self.assertEqual(result["status"], "verified")
        self.assertEqual(len(self.client.created), 2)

    def test_cleanup_failure_does_not_misreport_target_failure(self):
        self.failures["cleanup"] = True
        result = self.apply()
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["pending_cleanup"], "retry_required")
        self.assertTrue(result["verified"])
        self.assertEqual(len(self.rows), 2)
        self.failures.clear()
        with patch.object(app, 'utcnow', return_value=datetime.now(timezone.utc) + timedelta(hours=2)):
            again = self.apply()
        self.assertEqual(again["status"], "already_completed")
        self.assertEqual(again["pending_cleanup"], "removed")
        self.assertEqual(len(self.rows), 1)

    def test_unavailable_native_backend_is_not_misreported_as_missing_login(self):
        with patch.object(app, 'open_store', side_effect=VaultError(TOKEN)):
            result = self.apply()
        self.assertEqual(result['status'], 'keychain_unavailable')
        self.assertEqual(self.client.created, [])
        self.assert_no_leak(result)

    def test_crash_after_target_save_recovers_by_native_comparison_without_post(self):
        original = app.save_receipt
        failed = [False]
        def save(path, receipt):
            if receipt['target_saved'] and not failed[0]:
                failed[0] = True
                raise OSError(TOKEN + COOKIE)
            return original(path, receipt)
        with patch.object(app, 'save_receipt', side_effect=save):
            first = self.apply()
        self.assertEqual(first['status'], 'keychain_unavailable')
        self.assertEqual(self.rows[self.plan['keychain_account']], TOKEN)
        self.assertEqual(self.apply()['status'], 'verified')
        self.assertEqual(len(self.client.created), 1)
        self.assert_no_leak(first)

    def test_symlink_and_corrupt_receipts_do_not_leak_or_create(self):
        self.failures["target"] = True
        result = self.apply()
        receipt = Path(result["receipt_path"])
        receipt.write_text(json.dumps({"token": TOKEN, "cookie": COOKIE}))
        result = self.apply()
        self.assertEqual(result["status"], "invalid_operation")
        self.assertNotIn(TOKEN, json.dumps(result))
        receipt.unlink()
        secret = self.root / "unrelated"
        secret.write_text("keep")
        receipt.symlink_to(secret)
        self.assertEqual(self.apply()["status"], "invalid_operation")
        self.assertEqual(secret.read_text(), "keep")
        self.assertEqual(len(self.client.created), 1)

    def test_shared_account_lock_blocks_parallel_creation(self):
        scope = app.Scope.from_config(fixtures.config(), ACCOUNT)
        with app.operation_lock(self.directory, scope):
            self.assertEqual(self.apply()["status"], "operation_in_progress")
        self.assertEqual(self.client.created, [])

    def test_cli_returns_metadata_without_a_terminal_or_secret_output(self):
        output, error = io.StringIO(), io.StringIO()
        args = self.plan["apply_command"][2:]
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            code = workflow.main(args)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "verified")
        self.assertNotIn(TOKEN, output.getvalue() + error.getvalue())
        self.assertNotIn(COOKIE, output.getvalue() + error.getvalue())


class SessionTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.path = self.home / "Library/Application Support/Plane/Cookies"
        self.path.parent.mkdir(parents=True)
        self.db = sqlite3.connect(self.path)
        self.addCleanup(self.db.close)
        self.db.execute("create table cookies(host_key text, path text, name text, value text, encrypted_value blob, expires_utc integer, has_expires integer)")
        self.db.commit()
        for p in (patch.object(app.Path, "home", return_value=self.home), patch.object(app.sys, "platform", "darwin")):
            p.start(); self.addCleanup(p.stop)

    def add(self, name="session-id", value=COOKIE, encrypted=b"", expiry=0, host=".plane.so"):
        self.db.execute("insert into cookies values(?, '/', ?, ?, ?, ?, ?)", (host, name, value, encrypted, expiry, int(bool(expiry))))
        self.db.commit()

    def test_reads_live_wal_and_only_auth_cookie_names_and_clears_after_use(self):
        self.db.execute("pragma journal_mode=wal")
        self.db.execute("pragma wal_autocheckpoint=0")
        self.add()
        self.add(name="analytics", value="unrelated")
        self.assertTrue(Path(str(self.path) + "-wal").is_file())
        with app.app_session() as cookies:
            self.assertEqual(cookies, {"session-id": COOKIE})
        self.assertEqual(cookies, {})
        self.assertEqual(self.db.execute("select count(*) from cookies").fetchone()[0], 2)

    def test_missing_expired_and_encrypted_cookie_have_distinct_results(self):
        with self.assertRaises(app.CredentialError) as error:
            with app.app_session(): pass
        self.assertEqual(error.exception.code, "login_required")
        self.add(expiry=1)
        with self.assertRaises(app.CredentialError) as error:
            with app.app_session(): pass
        self.assertEqual(error.exception.code, "login_required")
        self.db.execute("delete from cookies"); self.db.commit()
        self.add(encrypted=b"synthetic-encrypted-data")
        with self.assertRaises(app.CredentialError) as error:
            with app.app_session(): pass
        self.assertEqual(error.exception.code, "session_unavailable")

    def test_wrong_host_and_duplicate_session_are_not_selected(self):
        self.add(host="unrelated.example")
        with self.assertRaises(app.CredentialError) as error:
            with app.app_session(): pass
        self.assertEqual(error.exception.code, "login_required")
        self.add(); self.add()
        with self.assertRaises(app.CredentialError) as error:
            with app.app_session(): pass
        self.assertEqual(error.exception.code, "session_unavailable")

    def test_error_in_caller_is_not_misclassified_as_session_failure(self):
        self.add()
        with self.assertRaises(OSError):
            with app.app_session(): raise OSError(TOKEN)


class BoundaryTests(unittest.TestCase):
    setUp = fixtures.RepositoryTests.setUp

    def test_other_platform_and_native_and_self_hosted_never_load_credentials(self):
        for platform, native, self_hosted in [("win32", False, False), ("darwin", True, False), ("darwin", False, True)]:
            cfg = fixtures.config()
            if native: cfg["sync"] = {"provider": "native"}
            if self_hosted: cfg["plane"].update(api_url="https://plane.example.test", app_url="https://plane.example.test")
            (self.root / ".plane-devflow.json").write_text(json.dumps(cfg))
            with patch.object(app.sys, "platform", platform), patch.object(app, "open_store", side_effect=AssertionError), \
                 patch.object(app, "app_session", side_effect=AssertionError):
                with self.assertRaises(app.CredentialError) as caught:
                    app.create(self.root, account=ACCOUNT, expires_at="2099-01-01T00:00:00Z")
                self.assertEqual(caught.exception.code, "unsupported")

    def test_no_apply_without_bound_plan_or_explicit_valid_expiry(self):
        with patch.object(app.sys, "platform", "darwin"), patch.object(app, "open_store", side_effect=AssertionError), \
             patch.object(app, "app_session", side_effect=AssertionError):
            for expiry in ["2020-01-01T00:00:00Z", "2099-01-01", TOKEN, None]:
                with self.assertRaises(app.CredentialError):
                    app.create(self.root, account=ACCOUNT, expires_at=expiry)
            with self.assertRaises(app.CredentialError):
                app.create(self.root, account=ACCOUNT, expires_at="2099-01-01T00:00:00Z", apply=True)


class HttpTests(unittest.TestCase):
    def test_exception_finalizers_cannot_emit_raw_error_text(self):
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always")
            client = app.CloudClient({"session-id": COOKIE})
            error = urllib.error.HTTPError(app.API, 403, TOKEN + COOKIE, {}, io.BytesIO(TOKEN.encode()))
            with patch.object(client.opener, "open", side_effect=error):
                with self.assertRaises(app.CredentialError): client.identity()
            error = None
            gc.collect()
        text = " ".join(str(item.message) for item in recorded)
        self.assertNotIn(TOKEN, text)
        self.assertNotIn(COOKIE, text)

    def test_errors_never_echo_http_body_or_credential_headers(self):
        for status, code in [(401, "login_required"), (403, "permission_denied"), (429, "rate_limited"), (503, "network_unavailable"), (302, "invalid_response")]:
            with self.subTest(status=status):
                client = app.CloudClient({"session-id": COOKIE})
                error = urllib.error.HTTPError(app.API, status, TOKEN + COOKIE, {}, io.BytesIO(TOKEN.encode()))
                with patch.object(client.opener, "open", side_effect=error):
                    with self.assertRaises(app.CredentialError) as caught: client.identity()
                self.assertEqual(caught.exception.code, code)
                self.assertNotIn(TOKEN, str(caught.exception))
                self.assertNotIn(COOKIE, str(caught.exception))

    def test_only_allowlisted_methods_paths_and_fixed_origin(self):
        client = app.CloudClient({"session-id": COOKIE})
        with patch.object(client.opener, "open", side_effect=AssertionError):
            for method, path in [("POST", "https://unrelated.example"), ("GET", "//unrelated.example/"), ("DELETE", app.TOKENS), ("POST", "/api/users/me/")]:
                with self.assertRaises(app.CredentialError): client.request(method, path)
        self.assertIsNone(app.NoRedirect().redirect_request(None, None, 302, "", {}, "https://unrelated.example"))

    def test_pat_verification_does_not_forward_session_cookie(self):
        client = app.CloudClient({"session-id": COOKIE})
        response = io.BytesIO(json.dumps({"id": "synthetic"}).encode())
        response.status = 200
        with patch.object(client.opener, "open", return_value=response) as request:
            client.request("GET", "/api/v1/users/me/", token=TOKEN)
        sent = request.call_args.args[0]
        self.assertEqual(sent.get_header("X-api-key"), TOKEN)
        self.assertIsNone(sent.get_header("Cookie"))


if __name__ == "__main__":
    unittest.main()
