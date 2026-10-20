# npm installation validation

Date: 2026-10-20. Candidate: 0.8.1. This change adds the complete npm plugin bundle and npx installer, English skill UI metadata, persistent owned marketplace storage, retained existing registrations, native file/skill verification and matching English/Chinese installation instructions.

## Required evidence

The final verification records the Node installer regression tests, full Python checks, exact packed file inventory, actual isolated npx installation/repetition/check, source retention and original-profile hash preservation. Package publication and the final public registry command are verified separately after the authorized publish. Live OAuth and business Plane/GitHub writeback remain outside installation verification.

## Local candidate evidence

- Python 3.14.3: all 255 tests passed in 139.812 seconds.
- Node.js 24.15.0: 18 installer regression tests passed, covering persistent sources after npx-cache removal, repeated installation, version updates, retained local/Git sources, read-only checks of an older installed version, registration/install failures and retries, incomplete skills/payloads, modified/unowned data, symlinks and live/stale installation locks. Native commands are simulated in these unit tests.
- Actual packed-tarball npx integration passed with Codex CLI 0.163.0. Fresh installation, repetition after npm-cache removal, read-only verification and a retained custom local source all use the actual CLI/native skill loader. All 28 plugin files match the reviewed source by SHA-256, and the three enabled names are Set Up Plane, Start Plane Task and Deliver Plane Task.
- A separate real Git-source retention check passed. Before source publication that test intentionally installed the existing public 0.8.0 source, and reported its real version/labels instead of claiming the 0.8.1 bundle had replaced the registration.
- The original Codex configuration, file-based authentication and npm configuration hashes were unchanged by the isolated integration run. No credentials were copied into temporary profiles; their file-based credential stores started without account authorization. A macOS sandbox separately denied writes to the real user directory.
- The npm file allowlist includes 28 plugin files plus the executable, implementation, package metadata, license and bilingual README files. Tests, evals, local evidence, Python bytecode and credentials are excluded.

During implementation, the first Node run exposed a fixture cleanup-order error; it was corrected before the passing run. Package validation also rejected treating the separate --check example as a second installation command; the validator now validates the actual first installation block. These failures were not treated as passing product checks.

Public registry installation, final tarball integrity and all cross-platform CI jobs must be read back after publication; local tarball success does not establish those external facts. Raw paths and original-profile metadata remain outside publishable files.

The first cross-platform CI run exposed Windows long/short path aliases in native cache verification; cache and managed-source identity now use filesystem directory identity. A subsequent run verified fresh/repeat/check installation on Windows, then found that native source-type metadata can be absent. The retained-source test now verifies the actual registered directory identity and unchanged source bytes instead of requiring that optional label; an omitted-type regression case was added. Earlier failed runs remain visible in CI history.
