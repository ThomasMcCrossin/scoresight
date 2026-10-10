"""OCR engine adapters and their automatic discovery.

To add an engine, drop a module in this folder (no registry to edit). It must:

  * define REQUIREMENTS, a list of pip requirement strings for its extra
    dependencies ([] if it only needs ScoreSight's requirements.txt);
  * define one or more subclasses of Engine with a unique `name`;
  * not import its optional dependencies at module level (import them in
    load() or recognize()), so that discovery works without them installed.

Every module here whose name doesn't start with "_" is imported by discover(),
and every Engine subclass defined in it with a non-empty `name` is collected.
"""

import importlib
import importlib.util
import pkgutil
import traceback
from dataclasses import dataclass, field
from typing import ClassVar, NamedTuple

import numpy as np


class Recognition(NamedTuple):
    """One crop's result. Adapters may return plain (text, confidence) tuples."""

    text: str
    # the engine's confidence in [0, 1], or None if it has none
    confidence: float | None = None
    # JSON-serializable extras kept with the prediction (e.g. a raw VLM answer,
    # or the pipeline's own filter state)
    info: dict | None = None


class EngineUnavailable(Exception):
    """Raised by load() when the engine can't run here (missing dependency,
    model, OS feature). The run is reported as skipped with the message."""


class Engine:
    """Base class of OCR engine adapters.

    Lifecycle, per (engine, variant) and dataset: unavailable_reason() is
    checked; __init__(variant); load() (timed: model loading); recognize() on
    batches of crops; close().
    """

    # unique engine name used on the command line: [a-z0-9_-]+
    name: ClassVar[str] = ""
    # the variants (e.g. models or preprocessing options) the engine can run
    variants: ClassVar[tuple[str, ...]] = ("default",)
    # the variants run when only the name is given; None means all of them
    default_variants: ClassVar[tuple[str, ...] | None] = None
    description: ClassVar[str] = ""
    # model size (parameters and/or download size), license and runtime, for
    # the report; info() can refine them per variant
    size: ClassVar[str] = ""
    license: ClassVar[str] = ""
    runtime: ClassVar[str] = ""
    # modules that must be importable; the default unavailable_reason() checks them
    imports: ClassVar[tuple[str, ...]] = ()
    # the largest batch recognize() is given (1: one crop per call)
    batch_size: ClassVar[int] = 1
    # set by discover() from the module's REQUIREMENTS
    requirements: ClassVar[list[str]] = []

    def __init__(self, variant: str | None = None):
        if variant is None:
            variant = self.variants[0]
        if variant not in self.variants:
            raise ValueError(
                f"{self.name} has no variant {variant!r} "
                f"(variants: {', '.join(self.variants)})"
            )
        self.variant = variant

    @classmethod
    def unavailable_reason(cls) -> str | None:
        """Why the engine can't run here, or None if it can. Must be cheap and
        must not import heavy dependencies; load() may still raise
        EngineUnavailable for problems only found when loading."""
        missing = [m for m in cls.imports if importlib.util.find_spec(m) is None]
        if missing:
            hint = (
                f" (pip install {' '.join(cls.requirements)})"
                if cls.requirements
                else ""
            )
            return f"missing Python modules: {', '.join(missing)}{hint}"
        return None

    def load(self) -> None:
        """Load models etc. Called once before the first recognize()."""

    def recognize(
        self, crops: list[np.ndarray], field_types: list[str]
    ) -> list[Recognition | tuple]:
        """Read each crop. crops are read-only C-contiguous uint8 BGR arrays
        (H, W, 3), at most batch_size of them; field_types gives each crop's
        field type (ocr_eval.fields.FIELD_TYPES) for engines that use it (e.g.
        character whitelists or prompts). Returns one Recognition (or (text,
        confidence) tuple) per crop, in order."""
        raise NotImplementedError

    def close(self) -> None:
        """Release models and processes."""

    def info(self) -> dict:
        """Metadata about this engine and variant, recorded with the results."""
        return {
            "name": self.name,
            "variant": self.variant,
            "description": self.description,
            "size": self.size,
            "license": self.license,
            "runtime": self.runtime,
            "requirements": list(self.requirements),
            "batch_size": self.batch_size,
        }

    @property
    def key(self) -> str:
        return f"{self.name}:{self.variant}"


@dataclass
class Registry:
    engines: dict[str, type[Engine]] = field(default_factory=dict)
    # module name -> traceback, for adapter modules that failed to import
    broken: dict[str, str] = field(default_factory=dict)

    def get(self, name: str) -> type[Engine]:
        try:
            return self.engines[name]
        except KeyError:
            raise KeyError(
                f"unknown engine {name!r} (known: {', '.join(sorted(self.engines))})"
            ) from None


def discover(package: str = __name__) -> Registry:
    """Import every module of the package (except those starting with "_") and
    collect the Engine subclasses defined in them."""
    registry = Registry()
    module = importlib.import_module(package)
    for entry in pkgutil.iter_modules(module.__path__):
        if entry.name.startswith("_"):
            continue
        module_name = f"{package}.{entry.name}"
        try:
            adapter = importlib.import_module(module_name)
        except Exception:
            registry.broken[module_name] = traceback.format_exc()
            continue
        requirements = list(getattr(adapter, "REQUIREMENTS", []))
        for value in vars(adapter).values():
            if (
                isinstance(value, type)
                and issubclass(value, Engine)
                and value is not Engine
                and value.__module__ == module_name
                and value.name
            ):
                if value.name in registry.engines:
                    other = registry.engines[value.name].__module__
                    registry.broken[module_name] = (
                        f"engine name {value.name!r} is already used by {other}"
                    )
                    continue
                value.requirements = requirements
                registry.engines[value.name] = value
    return registry


def parse_engine_spec(spec: str, registry: Registry) -> list[tuple[type[Engine], str]]:
    """'name' (its default variants), 'name:variant', 'name:v1,v2' or 'name:*'
    (every variant) -> [(engine class, variant)]."""
    name, _, variant_part = spec.partition(":")
    engine = registry.get(name.strip())
    if not variant_part:
        variants = engine.default_variants or engine.variants
    elif variant_part.strip() == "*":
        variants = engine.variants
    else:
        variants = [v.strip() for v in variant_part.split(",") if v.strip()]
    for variant in variants:
        if variant not in engine.variants:
            raise ValueError(
                f"{engine.name} has no variant {variant!r} "
                f"(variants: {', '.join(engine.variants)})"
            )
    return [(engine, variant) for variant in variants]
