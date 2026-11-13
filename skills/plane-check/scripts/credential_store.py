"""Opt-in local PAT storage. Native APIs only; no plaintext file fallback.

Manual credential commands and explicitly authorized Plane App creation use
values only in-process. Inspection returns presence/unknown, never a token or
a declaration of API readiness.
"""
import ctypes
import hashlib
import json
import sys
from contextlib import contextmanager
from dataclasses import dataclass

from plane_sync import WorkflowError, require


class VaultError(WorkflowError):
    """A deliberately non-secret error crossing the native API boundary."""


@dataclass(frozen=True)
class Scope:
    api_url: str
    workspace: str
    account: str

    @classmethod
    def from_config(cls, config, account):
        require(isinstance(account, str) and 0 < len(account.strip()) <= 256 and
                all(ord(c) >= 32 and ord(c) != 127 for c in account),
                "Specify the verified Plane account ID or email with --account.")
        # Validated config permits an origin only; host/scheme case and a final
        # slash must not make an existing saved entry appear missing.
        return cls(config["plane"]["api_url"].rstrip("/").lower(), config["plane"]["workspace"],
                   account.strip().casefold())

    @property
    def key(self):
        # Excludes project/repository: reuse across repositories, while keeping
        # different Plane instances, workspaces and accounts separate.
        encoded = json.dumps([self.api_url, self.workspace, self.account], ensure_ascii=True).encode()
        return "plane-devflow:" + hashlib.sha256(encoded).hexdigest()

    def metadata(self):
        return {"api_url": self.api_url, "workspace": self.workspace, "account": self.account}


def platform_backend():
    return {"darwin": "macos_keychain", "win32": "windows_credential_manager"}.get(sys.platform)


def validate_token(token):
    # No whitespace/control bytes, which also prevents stdin/header injection.
    require(isinstance(token, str) and 0 < len(token.encode("utf-8")) <= 2560 and
            all(33 <= ord(c) <= 126 for c in token), "Supply a non-empty PAT without whitespace (maximum 2560 bytes).")
    return token


class MacKeychain:
    """Generic passwords in the user's Keychain, accessed without shell arguments."""
    def __init__(self, scope):
        self.scope = scope
        self.cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        self.sec = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
        p, size = ctypes.c_void_p, ctypes.c_long
        signatures = {
            "CFStringCreateWithCString": ([p, ctypes.c_char_p, ctypes.c_uint32], p),
            "CFDataCreate": ([p, p, size], p),
            "CFDataGetLength": ([p], size), "CFDataGetBytePtr": ([p], p),
            "CFDictionaryCreateMutable": ([p, size, p, p], p),
            "CFDictionarySetValue": ([p, p, p], None), "CFRelease": ([p], None),
        }
        for name, (args, result) in signatures.items():
            method = getattr(self.cf, name)
            method.argtypes, method.restype = args, result
        for name, args in {"SecItemAdd": [p, ctypes.POINTER(p)],
                           "SecItemCopyMatching": [p, ctypes.POINTER(p)],
                           "SecItemUpdate": [p, p], "SecItemDelete": [p]}.items():
            method = getattr(self.sec, name)
            method.argtypes, method.restype = args, ctypes.c_int32

    def constant(self, name):
        library = self.cf if name.startswith("kCF") else self.sec
        return ctypes.c_void_p.in_dll(library, name).value

    @contextmanager
    def attributes(self, extra=(), token=None):
        owned = []
        try:
            query = self.cf.CFDictionaryCreateMutable(None, 0, None, None)
            if not query:
                raise VaultError("System credential storage is unavailable.")
            owned.append(query)
            pairs = [("kSecClass", self.constant("kSecClassGenericPassword"))]
            for key, value in (("kSecAttrService", "plane-devflow"), ("kSecAttrAccount", self.scope.key)):
                ref = self.cf.CFStringCreateWithCString(None, value.encode(), 0x08000100)
                if not ref:
                    raise VaultError("System credential storage is unavailable.")
                owned.append(ref)
                pairs.append((key, ref))
            pairs.extend((key, self.constant(value)) for key, value in extra)
            if token is not None:
                raw = token.encode("utf-8")
                buffer = ctypes.create_string_buffer(raw)
                try:
                    ref = self.cf.CFDataCreate(None, buffer, len(raw))
                finally:
                    ctypes.memset(buffer, 0, len(buffer))
                if not ref:
                    raise VaultError("System credential storage is unavailable.")
                owned.append(ref)
                pairs.append(("kSecValueData", ref))
            for key, value in pairs:
                self.cf.CFDictionarySetValue(query, self.constant(key), value)
            yield query
        finally:
            # Dictionary has no retain callbacks; release it before its values.
            if owned:
                self.cf.CFRelease(owned[0])
                for ref in reversed(owned[1:]):
                    self.cf.CFRelease(ref)

    def copy(self, *, data=False, interactive=True):
        extra = [("kSecReturnData" if data else "kSecReturnAttributes", "kCFBooleanTrue")]
        if not data or not interactive:
            # Read-only setup inspection must not trigger an unlock dialog.
            extra.append(("kSecUseAuthenticationUI", "kSecUseAuthenticationUIFail"))
        result = ctypes.c_void_p()
        try:
            with self.attributes(extra) as query:
                code = self.sec.SecItemCopyMatching(query, ctypes.byref(result))
            if code == -25300:  # errSecItemNotFound
                return None
            if code != 0:
                raise VaultError("Keychain is locked, access was denied, or storage is unavailable. Use the manual credential route.")
            if not result.value:
                raise VaultError("Saved credential is invalid; replace it explicitly.")
            if not data:
                return True
            length = self.cf.CFDataGetLength(result)
            if not 0 < length <= 2560:
                raise VaultError("Saved credential is invalid; replace it explicitly.")
            return ctypes.string_at(self.cf.CFDataGetBytePtr(result), length).decode("utf-8")
        finally:
            if result.value:
                self.cf.CFRelease(result)

    def contains(self):
        return self.copy() is not None

    def read(self, *, interactive=True):
        token = self.copy(data=True, interactive=interactive)
        require(token is not None, "No saved credential for this Plane account and workspace.")
        return validate_token(token)

    def save(self, token, *, replace=False, interactive=True):
        validate_token(token)
        extra = [] if interactive else [("kSecUseAuthenticationUI", "kSecUseAuthenticationUIFail")]
        with self.attributes(extra, token=token) as query:
            code = self.sec.SecItemAdd(query, None)
        if code == -25299:  # errSecDuplicateItem
            require(replace, "A credential is already saved. Use --replace only to replace it intentionally.")
            with self.attributes(extra) as query, self.attributes(token=token) as values:
                # SecItemUpdate accepts only changed attributes, not its class.
                self.cf.CFDictionaryRemoveValue.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
                self.cf.CFDictionaryRemoveValue.restype = None
                for key in ("kSecClass", "kSecAttrService", "kSecAttrAccount"):
                    self.cf.CFDictionaryRemoveValue(values, self.constant(key))
                code = self.sec.SecItemUpdate(query, values)
        if code != 0:
            raise VaultError("Could not save the credential in Keychain. Existing credentials were not deleted.")

    def delete(self, *, interactive=True):
        extra = [] if interactive else [("kSecUseAuthenticationUI", "kSecUseAuthenticationUIFail")]
        with self.attributes(extra) as query:
            code = self.sec.SecItemDelete(query)
        if code not in (0, -25300):
            raise VaultError("Could not remove the local Keychain credential.")


# Explicit Win32 widths also make the ABI testable from other platforms.
class FileTime(ctypes.Structure):
    _fields_ = [("low", ctypes.c_uint32), ("high", ctypes.c_uint32)]


class Credential(ctypes.Structure):
    _fields_ = [("Flags", ctypes.c_uint32), ("Type", ctypes.c_uint32),
                ("TargetName", ctypes.c_wchar_p), ("Comment", ctypes.c_wchar_p),
                ("LastWritten", FileTime), ("CredentialBlobSize", ctypes.c_uint32),
                ("CredentialBlob", ctypes.c_void_p), ("Persist", ctypes.c_uint32),
                ("AttributeCount", ctypes.c_uint32), ("Attributes", ctypes.c_void_p),
                ("TargetAlias", ctypes.c_wchar_p), ("UserName", ctypes.c_wchar_p)]


class WindowsCredentials:
    def __init__(self, scope):
        self.scope = scope
        self.api = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        p = ctypes.POINTER(Credential)
        signatures = {"CredReadW": ([ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(p)], ctypes.c_int),
                      "CredWriteW": ([p, ctypes.c_uint32], ctypes.c_int),
                      "CredDeleteW": ([ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32], ctypes.c_int),
                      "CredFree": ([ctypes.c_void_p], None)}
        for name, (args, result) in signatures.items():
            method = getattr(self.api, name)
            method.argtypes, method.restype = args, result

    @contextmanager
    def credential(self):
        pointer = ctypes.POINTER(Credential)()
        if not self.api.CredReadW(self.scope.key, 1, 0, ctypes.byref(pointer)):
            if ctypes.get_last_error() == 1168:  # ERROR_NOT_FOUND
                yield None
                return
            raise VaultError("Windows credential storage is unavailable or access was denied.")
        try:
            yield pointer.contents
        finally:
            if pointer:
                row = pointer.contents
                if row.CredentialBlob and 0 < row.CredentialBlobSize <= 2560:
                    ctypes.memset(row.CredentialBlob, 0, row.CredentialBlobSize)
                self.api.CredFree(pointer)

    def contains(self):
        # CredRead has no metadata-only mode. Do not convert its blob into a
        # Python value during inspection; wipe/free the native buffer promptly.
        with self.credential() as row:
            return row is not None

    def read(self):
        with self.credential() as row:
            require(row is not None, "No saved credential for this Plane account and workspace.")
            if not row.CredentialBlob or not 0 < row.CredentialBlobSize <= 2560:
                raise VaultError("Saved credential is invalid; replace it explicitly.")
            return validate_token(ctypes.string_at(row.CredentialBlob, row.CredentialBlobSize).decode("utf-8"))

    def save(self, token, *, replace=False):
        validate_token(token)
        require(replace or not self.contains(), "A credential is already saved. Use --replace only to replace it intentionally.")
        raw = token.encode("utf-8")
        buffer = ctypes.create_string_buffer(raw)
        row = Credential(Type=1, TargetName=self.scope.key, Comment="Plane DevFlow Actions PAT",
                         CredentialBlobSize=len(raw), CredentialBlob=ctypes.cast(buffer, ctypes.c_void_p),
                         Persist=2, UserName=self.scope.account)  # CRED_PERSIST_LOCAL_MACHINE
        try:
            if not self.api.CredWriteW(ctypes.byref(row), 0):
                raise VaultError("Could not save the Windows credential. Existing credentials were not deleted.")
        finally:
            ctypes.memset(buffer, 0, len(buffer))

    def delete(self):
        if not self.api.CredDeleteW(self.scope.key, 1, 0) and ctypes.get_last_error() != 1168:
            raise VaultError("Could not remove the local Windows credential.")


def open_store(scope):
    try:
        if sys.platform == "darwin":
            return MacKeychain(scope)
        if sys.platform == "win32":
            return WindowsCredentials(scope)
    except (OSError, AttributeError, ValueError):
        raise VaultError("System credential storage is unavailable. Use manual input; no file fallback is used.") from None
    raise VaultError("Local credential storage supports macOS and Windows. Use manual input on this platform.")


def inspect(config, account):
    scope = Scope.from_config(config, account)
    result = {**scope.metadata(), "backend": platform_backend(), "saved": None,
              "credential_value_returned": False, "credential_validity": "unverified"}
    try:
        result["saved"] = open_store(scope).contains()
        result["status"] = "saved" if result["saved"] else "missing"
    except VaultError:
        result["status"] = "unavailable"
    except (OSError, ValueError, TypeError, AttributeError):
        result["status"] = "unavailable"
    return result
