"""Download the pinned model files of engine variants, for CI.

    python -m ocr_eval.fetch_models ppocr:v6-small-wl,v6-tiny-wl [--attempts 4]
    python -m ocr_eval.fetch_models --pins ppocr:v6-small-wl,v6-tiny-wl

Downloads every file the variants' engines pin (an engine lists them with
pinned_files(): (Hugging Face repository, revision, file name)) into the
Hugging Face cache. --pins only prints them, one "repository@revision file"
line each, e.g. for a cache key that changes only when a pin does.

Network trouble is retried: connection errors and timeouts, HTTP 429 and 5xx
(waiting 10 s, then 30 s, 90 s, ...). Anything else fails at once: a revision
or file that doesn't exist, a repository that was renamed, removed or gated,
a missing package, an unknown engine or variant. Exit status: 0 when every file
is there, 75 (EX_TEMPFAIL) when the network still failed after the last
attempt, 1 for every other failure (2 for a bad command line). CI skips the
comparison only on 75, and only on pull requests.
"""

import argparse
import sys
import time

from ocr_eval import utf8_output

EXIT_TRANSIENT = 75  # sysexits.h EX_TEMPFAIL

# Errors that a retry can't fix, by class name (anywhere in the exception's
# class hierarchy or its chain of causes): the Hugging Face Hub's answers that
# the revision, file or repository doesn't exist or can't be read, and
# huggingface_hub's offline mode.
_PERMANENT = frozenset(
    {
        "RevisionNotFoundError",
        "RemoteEntryNotFoundError",
        "RepositoryNotFoundError",
        "GatedRepoError",
        "DisabledRepoError",
        "FileMetadataError",
        "OfflineModeIsEnabled",
    }
)
# Errors of the connection itself (httpx's TransportError covers its connect,
# read and timeout errors; requests' and the builtin ConnectionError and
# TimeoutError the rest).
_TRANSIENT = frozenset(
    {"TransportError", "TimeoutException", "ConnectionError", "TimeoutError"}
)


def _chain(error: BaseException):
    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        yield error
        error = error.__cause__ or error.__context__


def _class_names(error: BaseException) -> set[str]:
    return {cls.__name__ for cls in type(error).__mro__}


def is_transient(error: BaseException) -> bool:
    """True if a download failed because of the network or an overloaded
    server (worth retrying), False if it can't succeed as asked."""
    for cause in _chain(error):
        if _class_names(cause) & _PERMANENT:
            return False
        status = getattr(getattr(cause, "response", None), "status_code", None)
        if isinstance(status, int):
            return status == 429 or status >= 500
    return any(_class_names(cause) & _TRANSIENT for cause in _chain(error))


class TransientFailure(Exception):
    """The network still failed after the last attempt."""


def download_with_retries(
    download, repo: str, revision: str, filename: str, attempts: int, wait: float
):
    """download(repo, filename, revision=...) with retries of transient errors.
    Raises TransientFailure when the last attempt failed transiently, and the
    error itself when it isn't transient."""
    for attempt in range(1, attempts + 1):
        try:
            return download(repo, filename, revision=revision)
        except Exception as e:
            if not is_transient(e):
                raise
            if attempt == attempts:
                raise TransientFailure(
                    f"{repo}@{revision[:8]} {filename}: {type(e).__name__}: {e}"
                ) from e
            delay = wait * 3 ** (attempt - 1)
            print(
                f"{repo}@{revision[:8]} {filename}: {type(e).__name__}: {e}; "
                f"retrying in {delay:.0f} s ({attempt}/{attempts})",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(delay)


def pinned_files(specs: list[str]) -> list[tuple[str, str, str]]:
    """The (repository, revision, file name) the engine variants need, without
    duplicates, in order."""
    from ocr_eval.engines import discover, parse_engine_spec

    registry = discover()
    files = []
    for spec in specs:
        try:
            variants = parse_engine_spec(spec, registry)
        except KeyError:
            # an adapter that failed to import isn't registered: say why
            for module, error in registry.broken.items():
                print(f"{module} failed to import:\n{error}", file=sys.stderr)
            raise
        for engine_class, variant in variants:
            engine = engine_class(variant)
            if not hasattr(engine, "pinned_files"):
                raise ValueError(f"{engine.key} has no pinned model files")
            files += engine.pinned_files()
    return list(dict.fromkeys(files))


def main(argv=None, download=None) -> int:
    utf8_output()
    parser = argparse.ArgumentParser(
        prog="python -m ocr_eval.fetch_models",
        description="Download the pinned model files of engine variants.",
    )
    parser.add_argument("engine", nargs="+", help="ENGINE:VARIANT[,VARIANT...]")
    parser.add_argument(
        "--pins", action="store_true", help="only print the pinned files"
    )
    parser.add_argument("--attempts", type=int, default=4)
    parser.add_argument(
        "--wait", type=float, default=10.0, help="seconds before the first retry"
    )
    args = parser.parse_args(argv)
    try:
        files = pinned_files(args.engine)
    except (KeyError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.pins:
        for repo, revision, filename in files:
            print(f"{repo}@{revision} {filename}")
        return 0
    if download is None:
        try:
            from huggingface_hub import hf_hub_download as download
        except ImportError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
    for repo, revision, filename in files:
        try:
            path = download_with_retries(
                download, repo, revision, filename, max(1, args.attempts), args.wait
            )
        except TransientFailure as e:
            print(f"unavailable (network): {e}", file=sys.stderr)
            return EXIT_TRANSIENT
        except Exception as e:
            print(
                f"error: {repo}@{revision[:8]} {filename}: {type(e).__name__}: {e}",
                file=sys.stderr,
            )
            return 1
        print(f"{repo}@{revision[:8]} {filename}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
