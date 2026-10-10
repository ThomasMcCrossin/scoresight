"""Command line: python -m ocr_eval <command> (run it from the repository root)."""

import argparse
import json
import sys
from pathlib import Path

from ocr_eval.dataset import (
    DatasetError,
    list_datasets,
    load_dataset,
    read_manifest,
    validate_dataset,
)
from ocr_eval.fields import DISPLAY_TECHS, FIELD_TYPES, SPLITS


def _registry():
    from ocr_eval.engines import discover

    return discover()


def cmd_list(args) -> int:
    registry = _registry()
    datasets = []
    for path in list_datasets():
        samples, report, _ = read_manifest(path)
        counts = {}
        for sample in samples:
            counts[sample.field_type] = counts.get(sample.field_type, 0) + 1
        datasets.append(
            {
                "name": path.name,
                "path": str(path),
                "n": len(samples),
                "field_types": counts,
                "valid": report.ok,
            }
        )
    engines = []
    for name in sorted(registry.engines):
        engine = registry.engines[name]
        reason = engine.unavailable_reason()
        engines.append(
            {
                "name": name,
                "variants": list(engine.variants),
                "default_variants": list(engine.default_variants or engine.variants),
                "available": reason is None,
                "unavailable_reason": reason,
                "requirements": list(engine.requirements),
                "description": engine.description,
                "module": engine.__module__,
            }
        )
    if args.json:
        print(
            json.dumps(
                {
                    "datasets": datasets,
                    "engines": engines,
                    "broken_modules": registry.broken,
                },
                indent=2,
            )
        )
        return 0
    print("Datasets:")
    for d in datasets:
        types = ", ".join(f"{k} {v}" for k, v in sorted(d["field_types"].items()))
        flag = "" if d["valid"] else "  [INVALID: run validate]"
        print(f"  {d['name']:<24} {d['n']:>5} crops  ({types}){flag}")
    print("Engines:")
    for e in engines:
        state = (
            "available" if e["available"] else f"unavailable: {e['unavailable_reason']}"
        )
        print(f"  {e['name']:<24} {state}")
        print(f"    variants: {', '.join(e['variants'])}")
        if e["requirements"]:
            print(f"    requirements: {' '.join(e['requirements'])}")
    for module, problem in registry.broken.items():
        last = problem.strip().splitlines()[-1] if problem.strip() else problem
        print(f"  BROKEN adapter module {module}: {last}")
    return 0


def cmd_run(args) -> int:
    from ocr_eval.engines import parse_engine_spec
    from ocr_eval.report import render_report, write_results
    from ocr_eval.runner import RunOptions, run_all

    registry = _registry()
    engines = []
    try:
        for spec in args.engine:
            engines.extend(parse_engine_spec(spec, registry))
    except (KeyError, ValueError) as e:
        print(f"error: {e.args[0] if e.args else e}", file=sys.stderr)
        return 2
    for module, problem in registry.broken.items():
        print(f"warning: adapter module {module} failed to import", file=sys.stderr)
    splits = None
    if args.split:
        splits = [s.strip() for s in args.split.split(",") if s.strip()]
        unknown = [s for s in splits if s not in SPLITS]
        if unknown:
            print(f"error: unknown split {unknown[0]!r}", file=sys.stderr)
            return 2
    try:
        datasets = [
            load_dataset(ref, splits, args.limit, args.sample, args.seed)
            for ref in args.dataset
        ]
    except DatasetError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    log = None if args.quiet else (lambda message: print(message, flush=True))
    options = RunOptions(
        single_latency_samples=args.single_latency_samples, warmup=args.warmup
    )
    results = run_all(datasets, engines, options, label=args.label, log=log)
    out = Path(args.out)
    write_results(out / "results.json", results)
    report = render_report(results)
    (out / "report.md").write_text(report, encoding="utf-8", newline="\n")
    print(f"Wrote {out / 'results.json'} and {out / 'report.md'}")
    errors = [r for r in results["runs"] if r["status"] == "error"]
    for run in errors:
        print(f"error: {run['dataset']} {run['key']}: {run['reason']}", file=sys.stderr)
    return 1 if errors else 0


def cmd_compare(args) -> int:
    from ocr_eval.compare import compare_results, render_comparison
    from ocr_eval.report import read_results

    try:
        baseline = read_results(args.baseline)
        new = read_results(args.new)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    scorings = ("raw", "postfilter") if args.scoring == "both" else (args.scoring,)
    comparison = compare_results(
        baseline,
        new,
        max_drop=args.max_drop,
        scorings=scorings,
        alpha=args.alpha,
        require_all=args.require_all,
    )
    markdown = render_comparison(comparison, args.max_drop)
    if args.markdown:
        Path(args.markdown).parent.mkdir(parents=True, exist_ok=True)
        Path(args.markdown).write_text(markdown, encoding="utf-8", newline="\n")
    print(markdown)
    return 0 if comparison.ok else 1


def cmd_report(args) -> int:
    from ocr_eval.report import read_results, render_report

    try:
        results = read_results(args.results)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    report = render_report(results, max_examples=args.max_examples)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(report)
    return 0


def cmd_validate(args) -> int:
    status = 0
    for ref in args.dataset:
        report = validate_dataset(ref, strict_licenses=args.strict_licenses)
        for warning in report.warnings:
            print(f"{ref}: warning: {warning}")
        for error in report.errors:
            print(f"{ref}: error: {error}")
        if report.ok:
            print(f"{ref}: OK")
        else:
            status = 1
    return status


def cmd_import_dojo(args) -> int:
    from ocr_eval.dojo import import_dojo

    try:
        added, skipped = import_dojo(
            args.folder,
            args.out,
            author=args.author,
            license=args.license,
            attribution=args.attribution,
            source_url=args.source_url,
            field_type=args.field_type,
            display_tech=args.display_tech,
            include_unapproved=args.include_unapproved,
            prefix=args.prefix,
        )
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    reasons = {}
    for _, reason in skipped:
        reasons[reason] = reasons.get(reason, 0) + 1
    print(f"Added {added} crops to {args.out}.")
    for reason, count in sorted(reasons.items()):
        print(f"  skipped {count}: {reason}")
    report = validate_dataset(args.out)
    for error in report.errors:
        print(f"error: {error}", file=sys.stderr)
    return 0 if report.ok else 1


def cmd_requirements(args) -> int:
    registry = _registry()
    try:
        engines = [registry.get(name.partition(":")[0]) for name in args.engine]
    except KeyError as e:
        print(f"error: {e.args[0]}", file=sys.stderr)
        return 2
    seen = []
    for engine in engines:
        for requirement in engine.requirements:
            if requirement not in seen:
                seen.append(requirement)
    print("\n".join(seen))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ocr_eval",
        description="Evaluate OCR engines on scoreboard crop datasets.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    p = commands.add_parser("list", help="list datasets and engines (and availability)")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.set_defaults(func=cmd_list)

    p = commands.add_parser("run", help="run engines on datasets")
    p.add_argument(
        "--dataset",
        action="append",
        required=True,
        help="dataset name (in ocr_eval/datasets or $OCR_EVAL_DATASETS) or folder; repeatable",
    )
    p.add_argument(
        "--engine",
        action="append",
        required=True,
        help="NAME (its default variants), NAME:VARIANT, NAME:V1,V2 or NAME:*; repeatable",
    )
    p.add_argument(
        "--out", required=True, help="output folder (results.json, report.md)"
    )
    p.add_argument(
        "--split", help=f"comma-separated splits to keep ({', '.join(SPLITS)})"
    )
    p.add_argument(
        "--limit", type=int, help="first N crops of each dataset (quick runs)"
    )
    p.add_argument(
        "--sample",
        type=int,
        metavar="N",
        help="a stratified sample of N crops of each dataset (by field type, in "
        "proportion; reproducible): for slow engines",
    )
    p.add_argument("--seed", type=int, default=0, help="the --sample seed (default 0)")
    p.add_argument("--label", help="a name for this run, shown in the report")
    p.add_argument(
        "--single-latency-samples",
        type=int,
        default=50,
        metavar="N",
        help="crops timed one at a time for engines that batch (default 50)",
    )
    p.add_argument(
        "--warmup", type=int, default=1, help="untimed warm-up calls (default 1)"
    )
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_run)

    p = commands.add_parser(
        "compare", help="compare results with a baseline; exit 1 on a regression"
    )
    p.add_argument("baseline")
    p.add_argument("new")
    p.add_argument(
        "--max-drop",
        type=float,
        default=0.02,
        help="largest allowed drop in exact-match accuracy (default 0.02)",
    )
    p.add_argument("--scoring", choices=("raw", "postfilter", "both"), default="both")
    p.add_argument(
        "--alpha",
        type=float,
        help="also require a significant drop (McNemar p < ALPHA) to fail",
    )
    p.add_argument(
        "--require-all",
        action="store_true",
        help="fail if a baseline run is missing from the new results",
    )
    p.add_argument("--markdown", help="also write the comparison to this file")
    p.set_defaults(func=cmd_compare)

    p = commands.add_parser(
        "report", help="render the markdown report of a results file"
    )
    p.add_argument("results")
    p.add_argument("--out", help="write to this file instead of stdout")
    p.add_argument("--max-examples", type=int, default=25)
    p.set_defaults(func=cmd_report)

    p = commands.add_parser("validate", help="check datasets")
    p.add_argument("dataset", nargs="+")
    p.add_argument(
        "--strict-licenses",
        action="store_true",
        help="error on licenses that don't allow committing the data",
    )
    p.set_defaults(func=cmd_validate)

    p = commands.add_parser(
        "import-dojo", help="make a dataset from a Training Dojo folder"
    )
    p.add_argument("folder", help="the OCR training data folder reviewed in the Dojo")
    p.add_argument("--out", required=True, help="dataset folder to create or extend")
    p.add_argument("--author", required=True, help="who captured/labelled the crops")
    p.add_argument(
        "--license",
        required=True,
        help="license the contributor grants, e.g. CC0-1.0 or CC-BY-4.0",
    )
    p.add_argument("--attribution", help="attribution line (default: author, license)")
    p.add_argument("--source-url", help="where the footage comes from, if public")
    p.add_argument(
        "--field-type",
        default="auto",
        choices=("auto",) + FIELD_TYPES,
        help="field type of every crop (default: guessed from the text)",
    )
    p.add_argument("--display-tech", default="unknown", choices=DISPLAY_TECHS)
    p.add_argument(
        "--include-unapproved",
        action="store_true",
        help="also import unapproved samples (as model-assisted-unverified)",
    )
    p.add_argument("--prefix", default="dojo", help="id prefix (default dojo)")
    p.set_defaults(func=cmd_import_dojo)

    p = commands.add_parser("requirements", help="print engines' pip requirements")
    p.add_argument("engine", nargs="+")
    p.set_defaults(func=cmd_requirements)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
