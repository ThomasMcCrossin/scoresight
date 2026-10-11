"""Scoring: text normalization, per-item scores and aggregate metrics with 95%
confidence intervals.

Normalization (applied to both the prediction and the ground truth):
  * Unicode NFKC (full-width digits and colons become ASCII), then every
    whitespace character is removed: a box holds one value, and "1 2" for 12 is
    a correct read of the digits.
  * text and other fields are compared case-insensitively (casefold).
  * Nothing else: in particular a clock's separator must match. "12:34"
    (minutes:seconds) and "12.34" are different readings, ScoreSight's Time
    format regexes tell them apart, and an output showing the wrong one is
    wrong. The lenient "digits" metric below ignores separators.

Per-item scores:
  exact   normalized prediction == normalized truth
  digits  for score/clock/period/number: the digit sequences are equal (all
          non-digits removed, so "12.34" matches "12:34" and "1O" doesn't match
          "10"); for text/other: same as exact
  edits   Levenshtein distance between the normalized strings (for CER)
  empty   the normalized prediction is empty (no reading)

Aggregates: exact/digits accuracy and the empty-output rate with Wilson score
95% intervals; CER = total edits / total ground-truth characters, with a
percentile bootstrap 95% interval over items (fixed seed, so reproducible).

Clustered statistics: the crops of one photo share its board, lighting and
focus, so they aren't independent, and intervals or tests that treat them as
independent are too narrow or too confident. cluster_bootstrap_interval
resamples whole clusters (dataset.Sample.cluster: a photo, or the photos of
one board and game) and cluster_sign_flip_p compares two engines with a
paired permutation test on the per-cluster differences.
"""

import math
import unicodedata
from dataclasses import dataclass
from fractions import Fraction

import numpy as np

NUMERIC_FIELD_TYPES = ("score", "clock", "period", "number")
_ASCII_DIGITS = "0123456789"
BOOTSTRAP_SAMPLES = 2000
BOOTSTRAP_SEED = 0
# random sign patterns of cluster_sign_flip_p (its p-values are then at least
# 1 / 20001), and the most non-zero clusters for which it enumerates all 2^m
SIGN_FLIP_PERMUTATIONS = 20000
SIGN_FLIP_EXACT_MAX_CLUSTERS = 16


def normalize(text: str | None, field_type: str) -> str:
    value = unicodedata.normalize("NFKC", text or "")
    value = "".join(value.split())
    if field_type not in NUMERIC_FIELD_TYPES:
        value = value.casefold()
    return value


def digits_only(text: str) -> str:
    return "".join(char for char in text if char in _ASCII_DIGITS)


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current = [i]
        for j, char_b in enumerate(b, start=1):
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + (char_a != char_b),
                )
            )
        previous = current
    return previous[-1]


@dataclass(frozen=True)
class ItemScore:
    exact: bool
    digits: bool
    edits: int
    length: int
    empty: bool


def score_item(prediction: str | None, truth: str, field_type: str) -> ItemScore:
    pred = normalize(prediction, field_type)
    gold = normalize(truth, field_type)
    exact = pred == gold
    if field_type in NUMERIC_FIELD_TYPES:
        gold_digits = digits_only(gold)
        digits = bool(gold_digits) and digits_only(pred) == gold_digits
    else:
        digits = exact
    return ItemScore(
        exact=exact,
        digits=digits,
        edits=levenshtein(pred, gold),
        length=len(gold),
        empty=pred == "",
    )


def wilson_interval(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """The Wilson score interval for k successes in n trials."""
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return (max(0.0, center - half), min(1.0, center + half))


def rate(k: int, n: int) -> dict:
    low, high = wilson_interval(k, n)
    return {
        "value": (k / n) if n else None,
        "k": k,
        "n": n,
        "ci95": [round(low, 4), round(high, 4)],
    }


def bootstrap_ratio_interval(
    numerators, denominators, samples=BOOTSTRAP_SAMPLES, seed=BOOTSTRAP_SEED
) -> tuple[float, float]:
    """Percentile bootstrap 95% interval of sum(numerators) / sum(denominators),
    resampling items with replacement."""
    num = np.asarray(numerators, dtype=np.float64)
    den = np.asarray(denominators, dtype=np.float64)
    n = len(num)
    if n == 0:
        return (0.0, 0.0)
    rng = np.random.default_rng(seed)
    chunks = []
    # in chunks, to bound memory for large datasets
    chunk_size = max(1, min(samples, 2_000_000 // max(1, n)))
    done = 0
    while done < samples:
        size = min(chunk_size, samples - done)
        index = rng.integers(0, n, size=(size, n))
        totals = den[index].sum(axis=1)
        chunks.append(
            np.divide(
                num[index].sum(axis=1),
                totals,
                out=np.zeros(size),
                where=totals > 0,
            )
        )
        done += size
    ratios = np.concatenate(chunks)
    return (float(np.percentile(ratios, 2.5)), float(np.percentile(ratios, 97.5)))


def cer(items: list[ItemScore]) -> dict:
    edits = [item.edits for item in items]
    lengths = [item.length for item in items]
    total = sum(lengths)
    low, high = bootstrap_ratio_interval(edits, lengths)
    return {
        "value": (sum(edits) / total) if total else None,
        "edits": sum(edits),
        "chars": total,
        "ci95": [round(low, 4), round(high, 4)],
    }


def summarize_items(items: list[ItemScore]) -> dict:
    n = len(items)
    return {
        "n": n,
        "exact": rate(sum(item.exact for item in items), n),
        "digits": rate(sum(item.digits for item in items), n),
        "cer": cer(items),
        "empty_rate": rate(sum(item.empty for item in items), n),
    }


def summarize(scored: list[tuple[object, ItemScore]]) -> dict:
    """Aggregate metrics over (sample, ItemScore) pairs, overall and by the
    samples' field_type, display_tech and split."""
    summary = summarize_items([item for _, item in scored])
    for attribute in ("field_type", "display_tech", "split"):
        groups: dict[str, list[ItemScore]] = {}
        for sample, item in scored:
            groups.setdefault(getattr(sample, attribute), []).append(item)
        summary[f"by_{attribute}"] = {
            key: summarize_items(groups[key]) for key in sorted(groups)
        }
    return summary


def latency_summary(values_ms: list[float]) -> dict | None:
    if not values_ms:
        return None
    values = np.asarray(values_ms, dtype=np.float64)
    return {
        "n": int(values.size),
        "mean_ms": round(float(values.mean()), 3),
        "p50_ms": round(float(np.percentile(values, 50)), 3),
        "p95_ms": round(float(np.percentile(values, 95)), 3),
        "max_ms": round(float(values.max()), 3),
    }


def _cluster_sums(values, clusters) -> tuple[np.ndarray, np.ndarray]:
    """Per cluster (in order of first appearance): the sum of values and the
    number of items."""
    index: dict = {}
    keys = [index.setdefault(cluster, len(index)) for cluster in clusters]
    if len(keys) != len(values):
        raise ValueError("values and clusters differ in length")
    sums = np.bincount(
        keys, weights=np.asarray(values, np.float64), minlength=len(index)
    )
    sizes = np.bincount(keys, minlength=len(index)).astype(np.float64)
    return sums, sizes


def cluster_count(clusters) -> int:
    return len(set(clusters))


def cluster_bootstrap_interval(
    values, clusters, samples=BOOTSTRAP_SAMPLES, seed=BOOTSTRAP_SEED
) -> tuple[float, float]:
    """Percentile bootstrap 95% interval of the mean of values over items
    (1/0 for a right/wrong reading, or a paired difference -1/0/1), resampling
    the clusters with replacement (each resample's mean is its items' sum over
    its items' count). With one item per cluster it is the item bootstrap."""
    sums, sizes = _cluster_sums(values, clusters)
    k = len(sums)
    if k == 0:
        return (0.0, 0.0)
    rng = np.random.default_rng(seed)
    chunks = []
    chunk_size = max(1, min(samples, 2_000_000 // k))
    done = 0
    while done < samples:
        size = min(chunk_size, samples - done)
        index = rng.integers(0, k, size=(size, k))
        chunks.append(sums[index].sum(axis=1) / sizes[index].sum(axis=1))
        done += size
    means = np.concatenate(chunks)
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def cluster_sign_flip_p(
    differences,
    clusters,
    permutations=SIGN_FLIP_PERMUTATIONS,
    seed=BOOTSTRAP_SEED,
) -> float:
    """Two-sided p-value of a paired comparison of two engines that respects
    clusters. differences are per item, b - a (1 if only b read it, -1 if only
    a did, else 0). Under the null hypothesis the two engines are exchangeable
    on every crop, so each cluster's sum of differences is as likely to have
    either sign; the observed |sum over clusters| is compared with its
    distribution under random sign flips of the cluster sums. Exact (every
    sign pattern) when at most SIGN_FLIP_EXACT_MAX_CLUSTERS clusters have a
    non-zero sum, else Monte Carlo with a fixed seed: then p = (exceedances +
    1) / (permutations + 1), never below 1 / (permutations + 1). With one item
    per cluster it is a sign test of the discordant items, like McNemar's.
    1.0 when no cluster has a non-zero sum."""
    sums, _ = _cluster_sums(differences, clusters)
    sums = sums[sums != 0]
    m = len(sums)
    if m == 0:
        return 1.0
    observed = abs(sums.sum()) - 1e-9
    if m <= SIGN_FLIP_EXACT_MAX_CLUSTERS:
        patterns = (np.arange(2**m)[:, None] >> np.arange(m)) & 1
        totals = np.abs((patterns * 2 - 1) @ sums)
        return float(np.count_nonzero(totals >= observed) / len(totals))
    rng = np.random.default_rng(seed)
    exceed = done = 0
    chunk_size = max(1, min(permutations, 2_000_000 // m))
    while done < permutations:
        size = min(chunk_size, permutations - done)
        signs = rng.integers(0, 2, size=(size, m), dtype=np.int8) * 2 - 1
        exceed += int(np.count_nonzero(np.abs(signs @ sums) >= observed))
        done += size
    return (exceed + 1) / (permutations + 1)


def mcnemar_exact_p(b: int, c: int) -> float:
    """Two-sided exact McNemar test p-value for paired binary outcomes, given
    the discordant counts b (only the first system right) and c (only the second
    right). 1.0 when there are no discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1))
    return float(min(Fraction(1), Fraction(2 * tail, 2**n)))
