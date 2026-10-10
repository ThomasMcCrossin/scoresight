"""Packaging and release tooling: the version helpers, scripts/bump_version.py,
the frozen-app smoke test runner, and the consistency of scoresight.spec,
scoresight.iss and the workflows with the code and with each other."""

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

import version

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_script(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


versioning = _load_script("versioning", REPO_ROOT / "scripts" / "ci" / "versioning.py")
bump_version = _load_script("bump_version", REPO_ROOT / "scripts" / "bump_version.py")


# --- version parsing ----------------------------------------------------------


def test_read_version_matches_the_version_module():
    assert versioning.read_version() == version.__version__
    versioning.parse_version(version.__version__)


@pytest.mark.parametrize(
    "source, expected",
    [
        ('__version__ = "1.2.3"\n', "1.2.3"),
        ("'''Docs.'''\n\n__version__ = '1.2.3-rc.1'\nOTHER = 1\n", "1.2.3-rc.1"),
    ],
)
def test_read_version_parses_without_importing(tmp_path, source, expected):
    path = tmp_path / "version.py"
    path.write_text(source, encoding="utf-8")
    assert versioning.read_version(path) == expected


def test_read_version_requires_a_string_literal(tmp_path):
    path = tmp_path / "version.py"
    path.write_text("__version__ = get_version()\n", encoding="utf-8")
    with pytest.raises(ValueError, match="__version__"):
        versioning.read_version(path)


def test_versions_sort_prereleases_before_the_release():
    ordered = [
        "0.1.0",
        "0.2.0-beta.1",
        "0.2.0-beta.2",
        "0.2.0-beta.10",
        "0.2.0-rc.1",
        "0.2.0",
        "0.2.1",
        "0.10.0",
        "1.0.0",
    ]
    assert sorted(ordered, key=versioning.parse_version) == ordered


@pytest.mark.parametrize(
    "bad",
    ["v0.2.0", "0.2", "0.2.0.1", "0.2.0-alpha.1", "0.2.0rc1", "0.2.0-rc", "0.2.0 "],
)
def test_invalid_versions_are_rejected(bad):
    with pytest.raises(ValueError, match="invalid version"):
        versioning.parse_version(bad)


@pytest.mark.parametrize(
    "value, numeric, prerelease",
    [("0.2.0", "0.2.0.0", False), ("1.10.3-rc.2", "1.10.3.0", True)],
)
def test_numeric_version_and_prerelease(value, numeric, prerelease):
    assert versioning.numeric_version(value) == numeric
    assert versioning.is_prerelease(value) is prerelease


def test_package_label_marks_non_release_builds_with_the_commit():
    sha = "1a2b3c4d5e6f7a8b9c0d"
    assert versioning.package_label("0.2.0", release=True, sha=sha) == "0.2.0"
    assert versioning.package_label("0.2.0", release=False, sha=sha) == "0.2.0-1a2b3c4"
    assert versioning.package_label("0.2.0", release=False, sha=None) == "0.2.0"


def test_check_tag():
    versioning.check_tag("0.2.0-rc.1", "0.2.0-rc.1")
    with pytest.raises(ValueError, match="does not match"):
        versioning.check_tag("0.2.1", "0.2.0")
    with pytest.raises(ValueError, match="invalid version"):
        versioning.check_tag("v0.2.0", "0.2.0")


def test_check_tag_command(capsys):
    assert versioning.main(["check-tag", version.__version__]) == 0
    assert versioning.main(["check-tag", "999.0.0"]) == 1
    assert "does not match" in capsys.readouterr().err


def test_github_output(tmp_path, monkeypatch):
    output = tmp_path / "github_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    assert versioning.main(["github-output", "--sha", "abcdef0123456789"]) == 0
    values = dict(line.split("=", 1) for line in output.read_text().splitlines())
    current = version.__version__
    assert values == {
        "version": current,
        "label": f"{current}-abcdef0",
        "numeric": versioning.numeric_version(current),
        "prerelease": str(versioning.is_prerelease(current)).lower(),
    }


# --- CHANGELOG sections -------------------------------------------------------

CHANGELOG = """\
# Changelog

Intro text.

## [Unreleased]

### Added

- Profiles ([#8](https://github.com/royshil/scoresight/issues/8)).

### Fixed

- A crash.

## [0.1.0] - 2024-11-07

### Added

- UNO Essentials support.

## [0.0.1] - 2024-04-25

- First release.

[Unreleased]: https://github.com/royshil/scoresight/compare/0.1.0...HEAD
[0.1.0]: https://github.com/royshil/scoresight/compare/0.0.1...0.1.0
[0.0.1]: https://github.com/royshil/scoresight/releases/tag/0.0.1
"""


def test_changelog_section():
    assert versioning.changelog_section(CHANGELOG, "0.1.0") == (
        "### Added\n\n- UNO Essentials support.\n"
    )


def test_changelog_section_leaves_out_the_link_definitions():
    assert versioning.changelog_section(CHANGELOG, "0.0.1") == "- First release.\n"


@pytest.mark.parametrize("missing", ["0.2.0", "0.1", "0x1x0", "0.1.0-rc.1"])
def test_changelog_section_must_exist(missing):
    with pytest.raises(ValueError, match="no '## \\["):
        versioning.changelog_section(CHANGELOG, missing)


def test_changelog_section_must_not_be_empty():
    text = "## [0.3.0] - 2026-01-01\n\n## [0.2.0] - 2025-01-01\n\n- x\n"
    with pytest.raises(ValueError, match="empty"):
        versioning.changelog_section(text, "0.3.0")


def test_changelog_command(tmp_path, capsys):
    path = tmp_path / "CHANGELOG.md"
    path.write_text(CHANGELOG, encoding="utf-8")
    assert versioning.main(["changelog", "0.1.0", "--file", str(path)]) == 0
    assert "UNO Essentials support" in capsys.readouterr().out
    assert versioning.main(["changelog", "9.9.9", "--file", str(path)]) == 1


# --- scripts/bump_version.py --------------------------------------------------


@pytest.fixture
def release_files(tmp_path):
    version_file = tmp_path / "version.py"
    version_file.write_text(
        '"""Single source of truth."""\n\n__version__ = "0.1.0"\n', encoding="utf-8"
    )
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(CHANGELOG, encoding="utf-8")
    return version_file, changelog


def test_bump_version(release_files):
    version_file, changelog = release_files
    unreleased = versioning.changelog_section(
        CHANGELOG.replace("## [Unreleased]", "## [9.9.9]"), "9.9.9"
    )

    diff = bump_version.bump("0.2.0", "2026-10-10", version_file, changelog)

    assert versioning.read_version(version_file) == "0.2.0"
    text = changelog.read_text(encoding="utf-8")
    assert "## [Unreleased]\n\n## [0.2.0] - 2026-10-10\n\n### Added" in text
    # the old Unreleased notes are now the release notes of 0.2.0
    assert versioning.changelog_section(text, "0.2.0") == unreleased
    assert (
        "[Unreleased]: https://github.com/royshil/scoresight/compare/0.2.0...HEAD\n"
        in text
    )
    assert (
        "[0.2.0]: https://github.com/royshil/scoresight/compare/0.1.0...0.2.0\n" in text
    )
    assert text.count("## [Unreleased]") == 1
    assert '+__version__ = "0.2.0"' in diff


def test_bump_version_dry_run_writes_nothing(release_files):
    version_file, changelog = release_files
    diff = bump_version.bump(
        "0.2.0-rc.1", "2026-10-10", version_file, changelog, dry_run=True
    )
    assert versioning.read_version(version_file) == "0.1.0"
    assert changelog.read_text(encoding="utf-8") == CHANGELOG
    assert "+## [0.2.0-rc.1] - 2026-10-10" in diff


def test_bump_version_keeps_crlf_line_endings(release_files):
    version_file, changelog = release_files
    changelog.write_bytes(CHANGELOG.replace("\n", "\r\n").encode("utf-8"))
    bump_version.bump("0.2.0", "2026-10-10", version_file, changelog)
    data = changelog.read_bytes()
    assert b"\r\n## [0.2.0] - 2026-10-10\r\n" in data
    assert data.count(b"\n") == data.count(b"\r\n")


@pytest.mark.parametrize(
    "new_version, date, message",
    [
        ("0.1.0", "2026-10-10", "not newer"),
        ("0.1.0-rc.1", "2026-10-10", "not newer"),
        ("0.0.9", "2026-10-10", "not newer"),
        ("v0.2.0", "2026-10-10", "invalid version"),
        ("0.2.0", "10/10/2026", "invalid --date"),
    ],
)
def test_bump_version_refuses(release_files, new_version, date, message):
    version_file, changelog = release_files
    with pytest.raises(bump_version.BumpError, match=message):
        bump_version.bump(new_version, date, version_file, changelog)
    assert versioning.read_version(version_file) == "0.1.0"
    assert changelog.read_text(encoding="utf-8") == CHANGELOG


def test_bump_version_refuses_an_empty_unreleased_section(release_files):
    version_file, changelog = release_files
    bump_version.bump("0.2.0", "2026-10-10", version_file, changelog)
    with pytest.raises(bump_version.BumpError, match="empty"):
        bump_version.bump("0.2.1", "2026-10-11", version_file, changelog)
    assert versioning.read_version(version_file) == "0.2.0"


def test_bump_version_refuses_an_existing_section(release_files):
    version_file, changelog = release_files
    changelog.write_text(
        CHANGELOG.replace("## [0.0.1]", "## [0.3.0] - 2020-01-01\n\n- x\n\n## [0.0.1]"),
        encoding="utf-8",
    )
    with pytest.raises(bump_version.BumpError, match="already has"):
        bump_version.bump("0.3.0", "2026-10-10", version_file, changelog)


def test_bump_version_command(release_files, monkeypatch, capsys):
    version_file, changelog = release_files
    monkeypatch.setattr(bump_version, "VERSION_FILE", version_file)
    monkeypatch.setattr(bump_version, "CHANGELOG_FILE", changelog)

    assert bump_version.main(["0.2.0", "--dry-run"]) == 0
    assert "dry run" in capsys.readouterr().out
    assert versioning.read_version(version_file) == "0.1.0"

    assert bump_version.main(["0.2.0", "--date", "2026-10-10"]) == 0
    assert "git tag -a 0.2.0" in capsys.readouterr().out
    assert versioning.read_version(version_file) == "0.2.0"

    assert bump_version.main(["0.2.0"]) == 1
    assert "not newer" in capsys.readouterr().err


def test_bumped_version_file_stays_trivially_parseable(tmp_path):
    path = tmp_path / "version.py"
    path.write_text(
        Path(version.__file__).read_text(encoding="utf-8"), encoding="utf-8"
    )
    path.write_text(
        bump_version.bump_version_file(path.read_text(encoding="utf-8"), "9.8.7"),
        encoding="utf-8",
    )
    assert versioning.read_version(path) == "9.8.7"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assert not any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in tree.body)
