# TrainServe Sentinel — explanatory PDF source and guide

**Prepared for Ahmad Essam Abdelaziz, 3 November 2026.** The original five-page rendered PDF is saved separately in ChatGPT Library under `/CV Projects/TrainServe Sentinel/TrainServe_Sentinel_Explanation_2026-11-03.pdf`. This Markdown companion is an independently readable source and can be rendered as PDF.

## The problem and target users
An ML model can receive serving data whose schema, missingness, or feature distributions differ from training/reference data. Data scientists and ML platform engineers need a low-cost, reproducible quality gate before an inference batch proceeds. TrainServe Sentinel is an offline CSV scanner. It is not a predictive model, always-on monitoring service, or replacement for Evidently, Great Expectations or whylogs.

## Why this idea ranked first
The weighted editorial shortlist in `docs/RESEARCH.md` scores: TrainServe Sentinel 93/100, SQL Lineage Contract Checker 88, EdgeVision Failure Slice Evaluator 86, Distributed Feature Store Emulator 82, and LLM Retrieval Regression Bench 81. Hiring evidence emphasizes Python, testing, data pipelines, MLOps and reliable model operations. Scores are editorial and not hiring probabilities.

## Stack and architecture
Python >=3.10 standard library, CSV, JSON, argparse, static escaped HTML, unittest and GitHub Actions. No model subscription or paid service is needed.

Flow: baseline.csv -> parser and profile -> frozen baseline.json. Current.csv plus baseline.json -> schema/type/missingness checks -> numeric PSI and categorical JSD -> optional labelled accuracy delta -> priority policy -> JSON and HTML report -> exit code 0, 1 or 2.

Key files:
- `src/trainserve_sentinel/core.py`: CSV parser, baseline profile, policy, drift statistics, classification accuracy.
- `src/trainserve_sentinel/cli.py`: command-line arguments, atomic writes and explicit exit codes.
- `src/trainserve_sentinel/report.py`: standalone HTML with HTML-escaped user inputs.
- `scripts_generate.py`: fully synthetic deterministic sample generator.
- `tests/test_core.py`: unit, integration, malformed-input, HTML escaping and CLI behavior tests.
- `.github/workflows/ci.yml`: Python compilation, tests and end-to-end batch scans.
- `MASTER_PROMPT.md`: original reproducible specification and acceptance criteria.

## Install and run
Clone the repository, use Python 3.10+, and from the repo root set `PYTHONPATH=src` (on Windows PowerShell: `$env:PYTHONPATH="src"`). No external package installation is required for source-mode execution.

```bash
python -m trainserve_sentinel baseline --csv samples/baseline.csv --out artifacts/baseline.json --label label --prediction prediction
python -m trainserve_sentinel scan --baseline artifacts/baseline.json --csv samples/clean.csv --json artifacts/clean.json --html artifacts/clean.html
python -m trainserve_sentinel scan --baseline artifacts/baseline.json --csv samples/shifted.csv --json artifacts/shifted.json --html artifacts/shifted.html
PYTHONPATH=src python -m unittest discover -s tests -v
```

The clean scan exits 0 and prints PASS; the deliberately shifted scan exits 2 with FAIL, including numeric PSI, unseen-category, missingness and optional accuracy-drop findings. Input errors exit 1.

## Verification and limitations
34/34 unit and integration tests passed locally. Compilation and the clean/shifted smoke tests passed. The synthetic shifted input deliberately triggers eight failures; this is not a measured false-positive rate. PSI and JSD thresholds are heuristic, not hypothesis-test significance, and drift cannot establish causality for model failure. The system uses local, batch-only CSV and does not execute inference. See `docs/VERIFICATION.md` for exact results.

## Interview explanation
“I built a dependency-free Python gate that freezes an ML data contract and checks future batches for schema problems, increased missingness, categorical changes and numerical drift. I used fixed reference bins and an explicit policy so tests are reproducible. I included defensive CSV parsing, safe HTML reports, atomic output and exit codes for CI. The project has 34 passing tests and deliberately documented limitations: it is a heuristic batch gate, not an always-on production monitoring solution.”

## Truthful CV bullet
“Built TrainServe Sentinel, a Python standard-library ML data-quality and drift CI gate using PSI, Jensen–Shannon divergence, schema validation and optional labelled accuracy checks; verified with 34 automated tests and deterministic clean/shifted batch scenarios.”

## Publication and next improvements
GitHub repository: https://github.com/Ahmad-Joker/trainserve-sentinel
Feature branch: `feat/trainserve-sentinel-mvp`
Pull request is the authoritative source for the final commit and CI state. Improvements: configurable business-domain validation, drift-threshold calibration on real consented datasets, streaming connectors and model-service integration.
