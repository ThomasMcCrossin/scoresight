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
- Versions follow `MAJOR.MINOR.PATCH`. Pre-releases use `X.Y.Z-beta.N` or `X.Y.Z-rc.N`.
- Git tags are the bare version, **without** a `v` prefix (`0.2.0`, `0.2.0-rc.1`), matching the existing tags `0.0.1` to `0.1.0`.

## Changelog

`CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Every user-visible change in a pull request adds a line to the `## [Unreleased]` section under *Added*, *Changed*, *Deprecated*, *Removed*, *Fixed* or *Security*, with the issue number where there is one. Write entries for users, not developers.

## Release checklist

1. **Main is green**: CI passes on `main`, and the docs describe the new behaviour.
2. **Bump the version and changelog** on `main`:
   - set `__version__` in `src/version.py` to the new version,
   - rename `## [Unreleased]` in `CHANGELOG.md` to `## [X.Y.Z] - YYYY-MM-DD`, add a new empty `## [Unreleased]` section above it, and update the comparison links at the bottom.

   `scripts/bump_version.py` automates these edits. Run it with `--help` to see its options.
3. **Commit and tag**:

   ```bash
   git commit -am "Release X.Y.Z"
   git tag -a X.Y.Z -m "ScoreSight X.Y.Z"
   git push origin main X.Y.Z
   ```

4. **The release workflow runs** (`.github/workflows/release.yml`, triggered by the tag). It:
   - checks that the tag equals `src/version.py`, and fails otherwise,
   - builds Windows x64, macOS arm64, macOS x86_64 and Linux x86_64 packages (signing and notarizing the macOS app when the Apple secrets are configured),
   - runs the frozen app's `--self-test`,
   - uploads the packages and a `SHA256SUMS.txt`,
   - creates a **draft** GitHub release whose notes are this version's section from `CHANGELOG.md`.
5. **QA the draft**: download each package, install it, run through the [Quickstart](../quickstart.md) with a camera or video file, and check at least one output on each platform.
6. **Publish** the draft release on GitHub. For `-beta`/`-rc` tags, mark it as a pre-release.

If something is wrong, delete the draft and the tag, fix `main`, and tag again.

## Signing

- **macOS**: signing and notarization run only when the Apple secrets exist in the repository (see the build workflow for the secret names). Builds from forks and pull requests are unsigned.
- **Windows**: the installer is not code-signed yet, so users see SmartScreen warnings. The [installation guide](../INSTALL.md#windows) explains how to verify and run it.

## After the release

- Make sure the GitHub Pages docs (built from `docs/` on `main`) describe the released version.
- Reply on the issues fixed in the release, and close them.
