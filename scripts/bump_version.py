"""Prepare a release: set the version and cut the CHANGELOG section.

    python scripts/bump_version.py 0.2.0             # or 0.2.0-beta.1 / 0.2.0-rc.1
    python scripts/bump_version.py 0.2.0 --dry-run   # show the changes, write nothing

It sets `__version__` in src/version.py, renames CHANGELOG.md's
`## [Unreleased]` section to `## [X.Y.Z] - YYYY-MM-DD` (today, or --date), adds
a fresh empty `## [Unreleased]` above it, and updates the comparison links at the
bottom of the changelog. If src/version.py already has the new version (as for
the first release after the version was set during development), only the
CHANGELOG changes. It refuses to go backwards, to reuse a version that already
has a section, or to release an empty Unreleased section.

Afterwards, review and commit, then tag (the release workflow builds the tag):
    git commit -am "Release X.Y.Z"
    git tag -a X.Y.Z -m "ScoreSight X.Y.Z"
    git push origin main X.Y.Z
"""

import argparse
import datetime
import difflib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "ci"))

from versioning import (  # noqa: E402
    CHANGELOG_FILE,
    VERSION_FILE,
    parse_version,
    read_version,
)

# The (?=\r?$) lookaheads leave a CRLF file's line endings alone.
UNRELEASED_HEADING_RE = re.compile(r"^## \[Unreleased\][ \t]*(?=\r?$)", re.MULTILINE)
VERSION_ASSIGNMENT_RE = re.compile(
    r"""^(__version__\s*=\s*)(["'])([^"']*)\2""", re.MULTILINE
)
# "[Unreleased]: https://github.com/owner/repo/compare/0.1.0...HEAD"
UNRELEASED_LINK_RE = re.compile(
    r"^\[Unreleased\]:[ \t]*(?P<base>\S+/compare/)(?P<previous>[^\s.]\S*?)"
    r"\.\.\.HEAD[ \t]*(?=\r?$)",
    re.MULTILINE,
)


class BumpError(Exception):
    pass


def bump_version_file(text: str, new_version: str) -> str:
    matches = VERSION_ASSIGNMENT_RE.findall(text)
    if len(matches) != 1:
        raise BumpError("src/version.py must contain exactly one __version__ = '...'")
    return VERSION_ASSIGNMENT_RE.sub(
        lambda m: f"{m.group(1)}{m.group(2)}{new_version}{m.group(2)}", text
    )


def bump_changelog(text: str, new_version: str, date: str) -> str:
    if re.search(rf"^## \[{re.escape(new_version)}\]", text, re.MULTILINE):
        raise BumpError(f"CHANGELOG.md already has a '## [{new_version}]' section")
    heading = UNRELEASED_HEADING_RE.search(text)
    if heading is None:
        raise BumpError("CHANGELOG.md has no '## [Unreleased]' heading")
    next_heading = re.compile(r"^## ", re.MULTILINE).search(text, heading.end())
    body_end = next_heading.start() if next_heading else len(text)
    body = text[heading.end() : body_end]
    if not body.strip():
        raise BumpError(
            "the '## [Unreleased]' section of CHANGELOG.md is empty; "
            "describe the release's changes there first"
        )
    newline = "\r\n" if "\r\n" in text else "\n"
    new_heading = f"## [Unreleased]{newline}{newline}## [{new_version}] - {date}"
    text = text[: heading.start()] + new_heading + text[heading.end() :]

    link = UNRELEASED_LINK_RE.search(text)
    if link is not None:
        base, previous = link.group("base"), link.group("previous")
        links = (
            f"[Unreleased]: {base}{new_version}...HEAD{newline}"
            f"[{new_version}]: {base}{previous}...{new_version}"
        )
        text = text[: link.start()] + links + text[link.end() :]
    return text


def _read(path: Path) -> str:
    # newline="" keeps the file's own line endings
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def _write(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def _diff(path: Path, old: str, new: str) -> str:
    name = path.name
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            f"a/{name}",
            f"b/{name}",
        )
    )


def bump(
    new_version: str,
    date: str,
    version_file: Path,
    changelog_file: Path,
    dry_run: bool = False,
) -> str:
    """Apply (or with dry_run, only compute) the release edits; return the diff."""
    try:
        new_key = parse_version(new_version)
        current = read_version(version_file)
    except ValueError as e:
        raise BumpError(str(e)) from e
    try:
        current_key = parse_version(current)
    except ValueError:
        current_key = None  # an unparseable current version can always be replaced
    # Releasing the version src/version.py already has is allowed: then only
    # the CHANGELOG changes (and bump_changelog refuses a version that already
    # has a section, so nothing can be released twice).
    if current_key is not None and new_key < current_key:
        raise BumpError(f"{new_version} is older than the current version {current}")
    try:
        datetime.date.fromisoformat(date)
    except ValueError as e:
        raise BumpError(f"invalid --date {date!r}: {e}") from e

    old_version_text = _read(version_file)
    old_changelog = _read(changelog_file)
    new_version_text = bump_version_file(old_version_text, new_version)
    new_changelog = bump_changelog(old_changelog, new_version, date)
    if not dry_run:
        _write(version_file, new_version_text)
        _write(changelog_file, new_changelog)
    return _diff(version_file, old_version_text, new_version_text) + _diff(
        changelog_file, old_changelog, new_changelog
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Set src/version.py and move CHANGELOG.md's Unreleased "
        "section to a new release section.",
        epilog="Then: git commit -am 'Release X.Y.Z', git tag -a X.Y.Z -m "
        "'ScoreSight X.Y.Z', git push origin main X.Y.Z",
    )
    parser.add_argument(
        "version", help="new version: X.Y.Z, X.Y.Z-beta.N or X.Y.Z-rc.N"
    )
    parser.add_argument(
        "--date",
        default=datetime.date.today().isoformat(),
        help="release date for the CHANGELOG heading (default: today)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print the changes without writing"
    )
    args = parser.parse_args(argv)
    # the diff may contain characters the console's code page can't encode
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")

    try:
        diff = bump(args.version, args.date, VERSION_FILE, CHANGELOG_FILE, args.dry_run)
    except (BumpError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    sys.stdout.write(diff)
    if args.dry_run:
        print("\n(dry run: nothing was written)")
    else:
        print(
            f"\nsrc/version.py and CHANGELOG.md are ready for {args.version}. "
            "Review the changes, then:\n"
            f'  git commit -am "Release {args.version}"\n'
            f'  git tag -a {args.version} -m "ScoreSight {args.version}"\n'
            f"  git push origin main {args.version}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
