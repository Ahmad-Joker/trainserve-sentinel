"""CLI: baseline and scan; exit 0 success, 2 failed/inconclusive gate, 1 input/tool error."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from .core import DataError, build_baseline, scan
from .report import render_html


def _read_json(path: str) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DataError(f"Cannot load JSON {Path(path).name}: {exc}") from exc
    if not isinstance(data, dict):
        raise DataError("JSON root must be an object")
    return data


def _atomic_write(path: str, content: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".trainserve-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="trainserve-sentinel", description="Offline CSV train/serve drift and data quality CI gate")
    sub = p.add_subparsers(dest="command", required=True)
    base = sub.add_parser("baseline", help="Create a reference contract from a CSV")
    base.add_argument("--csv", required=True)
    base.add_argument("--out", required=True)
    base.add_argument("--ignore", default="", help="Comma-separated columns to ignore")
    base.add_argument("--label", help="Optional true-label column")
    base.add_argument("--prediction", help="Optional predicted-label column")
    base.add_argument("--policy", help="Optional JSON policy overrides")
    check = sub.add_parser("scan", help="Compare a current batch with a baseline contract")
    check.add_argument("--baseline", required=True)
    check.add_argument("--csv", required=True)
    check.add_argument("--json", required=True, help="Output report JSON")
    check.add_argument("--html", required=True, help="Output standalone HTML")
    check.add_argument("--policy", help="Optional JSON policy overrides")
    return p


def _ensure_distinct(inputs: list[str], outputs: list[str]) -> None:
    sources = {Path(x).resolve() for x in inputs}
    targets = [Path(x).resolve() for x in outputs]
    if len(set(targets)) != len(targets) or sources.intersection(targets):
        raise DataError("Output paths must be distinct and must not overwrite input files")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        policy = _read_json(args.policy) if args.policy else None
        if args.command == "baseline":
            _ensure_distinct([args.csv] + ([args.policy] if args.policy else []), [args.out])
            ignored = [x.strip() for x in args.ignore.split(",") if x.strip()]
            data = build_baseline(args.csv, ignored, args.label, args.prediction, policy)
            _atomic_write(args.out, json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n")
            print(f"Baseline created: {data['rows']} rows, {len(data['features'])} features -> {args.out}")
            return 0
        _ensure_distinct([args.baseline, args.csv] + ([args.policy] if args.policy else []), [args.json, args.html])
        baseline = _read_json(args.baseline)
        result = scan(baseline, args.csv, policy)
        _atomic_write(args.json, json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
        _atomic_write(args.html, render_html(result))
        print(f"Decision: {result['overall'].upper()} | {len(result['findings'])} checks | {args.json} | {args.html}")
        return 2 if result["overall"] in ("fail", "inconclusive") else 0
    except (DataError, OSError, TypeError, KeyError, ValueError, OverflowError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
