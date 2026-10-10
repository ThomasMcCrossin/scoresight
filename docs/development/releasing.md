---
title: Releasing
parent: Developer Guide
nav_order: 5
description: "How ScoreSight versions, changelogs, tags and the release workflow fit together."
---

# Releasing
{: .no_toc }

<details open markdown="block">
  <summary>On this page</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

## Versioning

- The version lives in **one** place: `__version__` in `src/version.py`. The window title, About dialog, update check, PyInstaller spec, Windows installer and release workflow all read it.
- Versions follow `MAJOR.MINOR.PATCH`. Pre-releases use `X.Y.Z-beta.N` or `X.Y.Z-rc.N`. No other formats are accepted.
- Git tags are the bare version, **without** a `v` prefix (`0.2.0`, `0.2.0-rc.1`), matching the existing tags `0.0.1` to `0.1.0`.

## Changelog

`CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Every user-visible change in a pull request adds a line to the `## [Unreleased]` section under *Added*, *Changed*, *Deprecated*, *Removed*, *Fixed* or *Security*, with the issue number where there is one. Write entries for users, not developers: the section becomes the release notes on GitHub.

## Release checklist

1. **Main is green**: CI passes on `main`, and the docs describe the new behaviour.
2. **Bump the version and changelog** on `main` with `scripts/bump_version.py`:

   ```bash
   python scripts/bump_version.py 0.2.0 --dry-run   # show the changes, write nothing
   python scripts/bump_version.py 0.2.0             # or 0.2.0-beta.1 / 0.2.0-rc.1
   ```

   It sets `__version__` in `src/version.py`, renames `## [Unreleased]` in `CHANGELOG.md` to `## [X.Y.Z] - YYYY-MM-DD` (today, or the date given with `--date YYYY-MM-DD`), adds a new empty `## [Unreleased]` section above it, and updates the comparison links at the bottom. It keeps the file's line endings. It refuses to go backwards, to reuse a version that already has a section, and to release an empty Unreleased section. If `src/version.py` already holds the new version (as it does for the first 0.2.0 release), only the changelog changes.
3. **Review, commit and tag**:

   ```bash
   git commit -am "Release X.Y.Z"
   git tag -a X.Y.Z -m "ScoreSight X.Y.Z"
   git push origin main X.Y.Z
   ```

4. **The release workflow runs** (`.github/workflows/release.yml`, triggered by tags `X.Y.Z`, `X.Y.Z-beta.N` and `X.Y.Z-rc.N`). It:
   - checks that the tag equals `src/version.py` and that `CHANGELOG.md` has a `## [X.Y.Z]` section, and fails otherwise,
   - builds Windows x64, macOS arm64, macOS x86_64 and Linux x86_64 packages with `build.yml` (signing and notarizing the macOS app and disk images when the Apple secrets are configured),
   - runs the frozen app's `--self-test` on every platform, and on Windows also installs, self-tests and uninstalls the installer,
   - checks that all five packages exist and writes `SHA256SUMS.txt`,
   - creates a **draft** GitHub release named "ScoreSight X.Y.Z" with the packages and `SHA256SUMS.txt` attached. Its notes are this version's section from `CHANGELOG.md`, followed by a downloads table and instructions for verifying the checksums. Beta and rc tags are marked as pre-releases automatically.
5. **QA the draft**: download each package, install it, run through the [Quickstart](../quickstart.md) with a camera or video file, and check at least one output on each platform.
6. **Publish** the draft release on GitHub.

If something is wrong, delete the draft and the tag, fix `main`, and tag again.

### Release assets

| File | Platform |
|---|---|
| `scoresight-X.Y.Z-windows-x64-setup.exe` | Windows installer |
| `scoresight-X.Y.Z-windows-x64-portable.zip` | Windows, no installation |
| `scoresight-X.Y.Z-macos-arm64.dmg` | macOS 15+, Apple Silicon |
| `scoresight-X.Y.Z-macos-x64.dmg` | macOS 15+, Intel |
| `scoresight-X.Y.Z-linux-x64.tar.gz` | Linux x86_64, glibc 2.35+ |
| `SHA256SUMS.txt` | Checksums of the five packages |

The README and the [installation guide](../INSTALL.md) refer to these names. If they change, update both.

## Signing

- **macOS**: signing and notarization run only for release builds, and only when the repository secrets exist: `APPLE_CERTIFICATE` (a base64-encoded Developer ID Application `.p12`), `APPLE_CERTIFICATE_PASSWORD` and `APPLE_APP_DEVELOPER_ID` (the signing identity) for signing, plus `APPLE_DEVELOPER_ID_USER`, `APPLE_DEVELOPER_ID_PASSWORD` (an app-specific password) and `APPLE_DEVELOPER_ID_TEAM` for notarization. Pull request and manual test builds are unsigned.
- **Windows**: the installer is not code-signed yet, so users see SmartScreen warnings. The [installation guide](../INSTALL.md#windows) explains how to verify and run it.

## After the release

- Make sure the GitHub Pages docs (built from `docs/` on `main`) describe the released version.
- Reply on the issues fixed in the release, and close them.
