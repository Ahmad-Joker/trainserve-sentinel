"""Offline, deterministic CSV train/serve monitoring. Standard library only."""
from __future__ import annotations

import bisect
import csv
import datetime as dt
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

VERSION = 1
MAX_ROWS = 200_000
MAX_COLUMNS = 200
DEFAULT_POLICY: dict[str, float | int] = {
    "min_rows": 30,
    "min_labeled_rows": 20,
    "missing_increase_warn": 0.07,
    "missing_increase_fail": 0.15,
    "numeric_psi_warn": 0.10,
    "numeric_psi_fail": 0.25,
    "categorical_js_warn": 0.05,
    "categorical_js_fail": 0.15,
    "unknown_category_warn": 0.03,
    "unknown_category_fail": 0.15,
    "out_of_range_warn": 0.05,
    "out_of_range_fail": 0.20,
    "accuracy_drop_warn": 0.05,
    "accuracy_drop_fail": 0.10,
    "constant_change_warn": 0.02,
    "constant_change_fail": 0.10,
}

class DataError(ValueError):
    """A safe user-facing input/contract error."""


def read_csv(path: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    p = Path(path)
    try:
        with p.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            header = next(reader, None)
            if header is None or not header or any(not c.strip() for c in header):
                raise DataError("CSV must have a nonempty header without blank column names")
            if len(header) > MAX_COLUMNS or len(set(header)) != len(header):
                raise DataError("CSV has too many columns or duplicate header names")
            rows = []
            for number, values in enumerate(reader, 2):
                if len(values) != len(header):
                    raise DataError(f"CSV row {number} has {len(values)} values, expected {len(header)}")
                rows.append(dict(zip(header, values)))
                if len(rows) > MAX_ROWS:
                    raise DataError(f"CSV exceeds supported {MAX_ROWS:,} rows")
    except (OSError, UnicodeError, csv.Error) as exc:
        raise DataError(f"Cannot read CSV {p.name}: {exc}") from exc
    if not rows:
        raise DataError("CSV must have at least one data row")
    return header, rows


def is_missing(value: str) -> bool:
    return value.strip().lower() in {"", "na", "n/a", "null", "none", "nan"}


def number(value: str) -> float | None:
    if is_missing(value):
        return None
    try:
        val = float(value)
    except (ValueError, OverflowError):
        return None
    return val if math.isfinite(val) else None


def _numeric_edges(values: list[float]) -> list[float]:
    ordered = sorted(values)
    n = len(ordered)
    # Linear interpolation, fixed at baseline time, deduplicated.
    def quantile(q: float) -> float:
        pos = (n - 1) * q
        lo = int(pos)
        hi = min(lo + 1, n - 1)
        return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)
    return sorted(set(quantile(i / 5) for i in range(1, 5)))


def _counts(values: list[float], edges: list[float]) -> list[int]:
    counts = [0] * (len(edges) + 1)
    for value in values:
        counts[bisect.bisect_right(edges, value)] += 1
    return counts


def _psi(base: list[int], current: list[int]) -> float:
    k = len(base)
    if k != len(current) or not k:
        raise DataError("Incompatible numeric histograms")
    a = sum(base) + 0.5 * k
    b = sum(current) + 0.5 * k
    return sum(((x + 0.5) / a - (y + 0.5) / b) *
               math.log(((x + 0.5) / a) / ((y + 0.5) / b))
               for x, y in zip(base, current))


def _jsd(base: dict[str, int], current: dict[str, int]) -> float:
    keys = set(base) | set(current)
    a = sum(base.values())
    b = sum(current.values())
    if not a or not b:
        return 0.0
    total = 0.0
    for key in keys:
        p, q = base.get(key, 0) / a, current.get(key, 0) / b
        mid = (p + q) / 2
        if p:
            total += 0.5 * p * math.log2(p / mid)
        if q:
            total += 0.5 * q * math.log2(q / mid)
    return max(0.0, min(1.0, total))


def _accuracy(rows: list[dict[str, str]], label: str, prediction: str) -> tuple[float | None, int]:
    pairs = [(r[label], r[prediction]) for r in rows if not is_missing(r[label]) and not is_missing(r[prediction])]
    return (sum(a == b for a, b in pairs) / len(pairs) if pairs else None, len(pairs))


def validate_policy(custom: dict[str, Any] | None = None) -> dict[str, float | int]:
    policy = dict(DEFAULT_POLICY)
    if custom:
        unknown = set(custom) - set(policy)
        if unknown:
            raise DataError("Unknown policy key(s): " + ", ".join(sorted(unknown)))
        policy.update(custom)
    for key, value in policy.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise DataError(f"Policy {key} must be a finite number")
        if key.startswith("min_"):
            if int(value) != value or value < 1:
                raise DataError(f"Policy {key} must be a positive integer")
            policy[key] = int(value)
        elif value < 0 or (key.endswith(("_increase_warn", "_increase_fail", "_rate_warn", "_rate_fail", "_drop_warn", "_drop_fail", "_change_warn", "_change_fail")) and value > 1):
            raise DataError(f"Policy {key} is out of range")
    for prefix in ("missing_increase", "numeric_psi", "categorical_js", "unknown_category", "out_of_range", "accuracy_drop", "constant_change"):
        if policy[f"{prefix}_warn"] > policy[f"{prefix}_fail"]:
            raise DataError(f"Policy {prefix}: warn threshold exceeds fail threshold")
    return policy


def build_baseline(csv_path: str | Path, ignore: list[str] | None = None,
                   label: str | None = None, prediction: str | None = None,
                   policy: dict[str, Any] | None = None) -> dict[str, Any]:
    header, rows = read_csv(csv_path)
    if bool(label) != bool(prediction):
        raise DataError("--label and --prediction must be provided together")
    ignored = set(ignore or [])
    if label:
        ignored.update({label, prediction})
    absent = ignored - set(header)
    if absent:
        raise DataError("Ignored or performance columns missing: " + ", ".join(sorted(absent)))
    features: dict[str, Any] = {}
    for name in header:
        if name in ignored:
            continue
        values = [r[name] for r in rows]
        present = [v for v in values if not is_missing(v)]
        if not present:
            raise DataError(f"Baseline feature '{name}' contains only missing values")
        missing_rate = 1 - len(present) / len(values)
        parsed = [number(v) for v in present]
        if all(v is not None for v in parsed):
            numeric = [v for v in parsed if v is not None]
            lo, hi = min(numeric), max(numeric)
            edges = _numeric_edges(numeric) if lo != hi else []
            features[name] = {"kind": "numeric", "missing_rate": missing_rate,
                              "min": lo, "max": hi, "edges": edges,
                              "counts": _counts(numeric, edges), "non_missing": len(numeric)}
        else:
            categories = dict(sorted(Counter(present).items()))
            features[name] = {"kind": "categorical", "missing_rate": missing_rate,
                              "categories": categories, "non_missing": len(present)}
    if not features:
        raise DataError("No features remain after exclusions")
    performance = None
    if label and prediction:
        accuracy, count = _accuracy(rows, label, prediction)
        performance = {"label": label, "prediction": prediction,
                       "accuracy": accuracy, "evaluated_rows": count}
    return {"version": VERSION, "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "source": Path(csv_path).name, "rows": len(rows), "features": features,
            "performance": performance, "policy": validate_policy(policy)}


def validate_baseline(baseline: dict[str, Any]) -> None:
    if not isinstance(baseline, dict) or baseline.get("version") != VERSION:
        raise DataError("Unsupported baseline version")
    if not isinstance(baseline.get("features"), dict) or not baseline["features"]:
        raise DataError("Baseline features are missing")
    if not isinstance(baseline.get("rows"), int) or baseline["rows"] < 1:
        raise DataError("Baseline row count is invalid")
    if not isinstance(baseline.get("policy", {}), dict):
        raise DataError("Baseline policy must be a JSON object")
    validate_policy(baseline.get("policy"))
    perf = baseline.get("performance")
    if perf is not None:
        if not isinstance(perf, dict) or not isinstance(perf.get("label"), str) or not isinstance(perf.get("prediction"), str):
            raise DataError("Invalid baseline performance configuration")
        acc, evaluated = perf.get("accuracy"), perf.get("evaluated_rows")
        if (acc is not None and (not isinstance(acc, (int, float)) or not math.isfinite(acc) or not 0 <= acc <= 1)) or not isinstance(evaluated, int) or evaluated < 0:
            raise DataError("Invalid baseline performance statistics")
    for name, feature in baseline["features"].items():
        if not isinstance(name, str) or not isinstance(feature, dict):
            raise DataError("Malformed baseline feature")
        if feature.get("kind") == "numeric":
            edges, counts = feature.get("edges"), feature.get("counts")
            if not isinstance(edges, list) or not isinstance(counts, list) or len(counts) != len(edges) + 1:
                raise DataError(f"Invalid numeric bins for {name}")
            if not all(isinstance(x, (int, float)) and math.isfinite(x) for x in edges):
                raise DataError(f"Non-finite bin edge for {name}")
            if edges != sorted(set(edges)):
                raise DataError(f"Unsorted or repeated bin edges for {name}")
            if not all(type(x) is int and x >= 0 for x in counts) or sum(counts) < 1:
                raise DataError(f"Invalid histogram for {name}")
            if feature.get("non_missing") != sum(counts):
                raise DataError(f"Inconsistent histogram total for {name}")
            if not all(isinstance(feature.get(k), (int, float)) and math.isfinite(feature[k]) for k in ("min", "max")):
                raise DataError(f"Invalid range for {name}")
        elif feature.get("kind") == "categorical":
            cats = feature.get("categories")
            if not isinstance(cats, dict) or not cats or not all(isinstance(k, str) and type(v) is int and v >= 0 for k, v in cats.items()):
                raise DataError(f"Invalid categories for {name}")
            if feature.get("non_missing") != sum(cats.values()) or not sum(cats.values()):
                raise DataError(f"Inconsistent category counts for {name}")
        else:
            raise DataError(f"Unknown feature kind for {name}")
        missing = feature.get("missing_rate")
        if not isinstance(missing, (int, float)) or not math.isfinite(missing) or not 0 <= missing <= 1:
            raise DataError(f"Invalid missing rate for {name}")


def _finding(feature: str, check: str, value: float | int | None,
             status: str, message: str, threshold: float | None = None) -> dict[str, Any]:
    return {"feature": feature, "check": check, "value": round(value, 6) if value is not None else None,
            "status": status, "threshold": threshold, "message": message}


def _level(value: float, warn: float, fail: float) -> str:
    return "fail" if value > fail else "warn" if value > warn else "pass"


def scan(baseline: dict[str, Any], csv_path: str | Path,
         policy_override: dict[str, Any] | None = None) -> dict[str, Any]:
    validate_baseline(baseline)
    policy = validate_policy({**baseline.get("policy", {}), **(policy_override or {})})
    header, rows = read_csv(csv_path)
    names = set(baseline["features"])
    actual = set(header)
    findings: list[dict[str, Any]] = []
    small_batch = len(rows) < policy["min_rows"] or baseline["rows"] < policy["min_rows"]
    if small_batch:
        findings.append(_finding("__batch__", "sample_size", len(rows), "inconclusive",
                                 f"Need at least {policy['min_rows']} rows in both batches"))
    for name in sorted(names - actual):
        findings.append(_finding(name, "schema_missing", None, "fail", "Required feature is absent"))
    perf = baseline.get("performance") or {}
    extras = actual - names - {perf.get("label"), perf.get("prediction")}
    for name in sorted(extras):
        findings.append(_finding(name, "schema_extra", None, "warn", "Unexpected extra column; ignored"))
    for name, feature in baseline["features"].items():
        if name not in actual:
            continue
        raw = [r[name] for r in rows]
        present = [v for v in raw if not is_missing(v)]
        missing_rate = 1 - len(present) / len(rows)
        if small_batch:
            if feature["kind"] == "numeric":
                invalid = sum(number(v) is None for v in present)
                if invalid:
                    findings.append(_finding(name, "numeric_type_errors", invalid, "fail",
                                             "Non-numeric or non-finite values in numeric feature"))
            continue  # A tiny sample cannot support stable distribution comparisons.
        increase = missing_rate - feature["missing_rate"]
        status = _level(increase, policy["missing_increase_warn"], policy["missing_increase_fail"])
        findings.append(_finding(name, "missing_rate_increase", increase, status,
                                 f"Current missing rate {missing_rate:.1%}; baseline {feature['missing_rate']:.1%}",
                                 policy[f"missing_increase_{'fail' if status == 'fail' else 'warn'}"]))
        if not present:
            findings.append(_finding(name, "distribution", None, "inconclusive", "No nonmissing values to compare"))
            continue
        if feature["kind"] == "numeric":
            parsed = [number(v) for v in present]
            invalid = sum(v is None for v in parsed)
            if invalid:
                findings.append(_finding(name, "numeric_type_errors", invalid, "fail",
                                         "Non-numeric or non-finite values in numeric feature"))
            vals = [v for v in parsed if v is not None]
            if not vals:
                findings.append(_finding(name, "numeric_distribution", None, "inconclusive", "No valid numeric values"))
                continue
            out_rate = sum(v < feature["min"] or v > feature["max"] for v in vals) / len(vals)
            status = _level(out_rate, policy["out_of_range_warn"], policy["out_of_range_fail"])
            findings.append(_finding(name, "out_of_baseline_range", out_rate, status,
                                     "Share outside baseline observed min/max; not a hard domain rule",
                                     policy[f"out_of_range_{'fail' if status == 'fail' else 'warn'}"]))
            if feature["min"] == feature["max"]:
                changed = sum(v != feature["min"] for v in vals) / len(vals)
                status = _level(changed, policy["constant_change_warn"], policy["constant_change_fail"])
                findings.append(_finding(name, "constant_changed", changed, status,
                                         "Baseline feature was constant; fraction of changed values",
                                         policy[f"constant_change_{'fail' if status == 'fail' else 'warn'}"]))
            else:
                psi = _psi(feature["counts"], _counts(vals, feature["edges"]))
                status = _level(psi, policy["numeric_psi_warn"], policy["numeric_psi_fail"])
                findings.append(_finding(name, "numeric_psi", psi, status,
                                         "Population Stability Index (smoothed, baseline fixed bins)",
                                         policy[f"numeric_psi_{'fail' if status == 'fail' else 'warn'}"]))
        else:
            counts = dict(Counter(present))
            unknown = sum(count for cat, count in counts.items() if cat not in feature["categories"]) / len(present)
            status = _level(unknown, policy["unknown_category_warn"], policy["unknown_category_fail"])
            findings.append(_finding(name, "unknown_category_rate", unknown, status,
                                     "Fraction of nonmissing values unseen in baseline",
                                     policy[f"unknown_category_{'fail' if status == 'fail' else 'warn'}"]))
            jsd = _jsd(feature["categories"], counts)
            status = _level(jsd, policy["categorical_js_warn"], policy["categorical_js_fail"])
            findings.append(_finding(name, "categorical_js", jsd, status,
                                     "Jensen-Shannon divergence in bits, range [0,1]",
                                     policy[f"categorical_js_{'fail' if status == 'fail' else 'warn'}"]))
    if perf:
        label, prediction = perf.get("label"), perf.get("prediction")
        if not label or not prediction or label not in actual or prediction not in actual:
            findings.append(_finding("__performance__", "accuracy", None, "inconclusive",
                                     "Paired label/prediction columns unavailable"))
        else:
            acc, count = _accuracy(rows, label, prediction)
            base_acc = perf.get("accuracy")
            if count < policy["min_labeled_rows"] or perf.get("evaluated_rows", 0) < policy["min_labeled_rows"] or base_acc is None:
                findings.append(_finding("__performance__", "accuracy", None, "inconclusive",
                                         "Insufficient paired labeled rows for accuracy comparison"))
            else:
                drop = base_acc - acc
                status = _level(drop, policy["accuracy_drop_warn"], policy["accuracy_drop_fail"])
                findings.append(_finding("__performance__", "accuracy_drop", drop, status,
                                         f"Current accuracy {acc:.1%} ({count} labeled); baseline {base_acc:.1%}",
                                         policy[f"accuracy_drop_{'fail' if status == 'fail' else 'warn'}"]))
    statuses = {f["status"] for f in findings}
    overall = next((x for x in ("fail", "inconclusive", "warn", "pass") if x in statuses), "pass")
    return {"version": VERSION, "baseline_source": baseline.get("source"), "current_source": Path(csv_path).name,
            "baseline_rows": baseline["rows"], "current_rows": len(rows), "overall": overall,
            "counts": dict(Counter(f["status"] for f in findings)), "policy": policy,
            "findings": findings,
            "interpretation": "Heuristic batch checks only; drift does not prove prediction quality loss."}
