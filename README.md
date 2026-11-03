# TrainServe Sentinel

**Dependency-free batch train/serve drift and data quality CI gate.** Compare a current CSV with a frozen reference dataset, explain each change and return a CI-friendly exit code. Built as a standalone portfolio project for ML/data engineering and MLOps reliability.

## What it detects

- Required feature columns missing; unexpected extra columns (warning)
- Increased missing-value rates and invalid numeric values
- Numeric drift using fixed-baseline quantile bins and smoothed Population Stability Index (PSI)
- Out-of-baseline numeric values and changed constant features
- Categorical drift using Jensen-Shannon divergence (JSD, 0–1 bits) and unseen categories
- Optional labeled classification accuracy drop (only if both datasets include paired true and predicted labels)
- Insufficient sample sizes (inconclusive, fails closed in CI)

No raw records are embedded in reports. The data and computations stay on your computer.

## Quick start (Python 3.10+, no pip install required)

```bash
# from repository root
export PYTHONPATH=src  # macOS/Linux
# Windows PowerShell: $env:PYTHONPATH = "src"
python -m trainserve_sentinel baseline --csv samples/baseline.csv --out artifacts/baseline.json --label label --prediction prediction
python -m trainserve_sentinel scan --baseline artifacts/baseline.json --csv samples/clean.csv --json artifacts/clean.json --html artifacts/clean.html
python -m trainserve_sentinel scan --baseline artifacts/baseline.json --csv samples/shifted.csv --json artifacts/shifted.json --html artifacts/shifted.html
```

Alternatively, install as a CLI: `python -m pip install -e .` and run `trainserve-sentinel` (requires pip/setuptools, not required for source usage). Open the HTML report locally in a browser.

Expected: clean exits `0` with `PASS`; shifted exits `2` with `FAIL` and a detailed report. Input/config errors exit `1`. A `WARN` status exits `0`; `INCONCLUSIVE` exits `2`. This is a deliberately conservative policy and can be customized.

### Customize thresholds

Create `policy.json` (all keys optional):

```json
{"numeric_psi_warn": 0.10, "numeric_psi_fail": 0.25, "categorical_js_fail": 0.15, "min_rows": 30}
```

Pass `--policy policy.json` to either `baseline` (persist defaults) or `scan` (override). See `src/trainserve_sentinel/core.py` for all supported keys. `--ignore id,internal_note` excludes non-features at baseline creation. Provide `--label` and `--prediction` together to enable optional accuracy monitoring.

### Run tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python -m compileall -q src tests
```

PowerShell: `$env:PYTHONPATH = "src"; python -m unittest discover -s tests -v`

## Architecture

```text
baseline.csv --[CSV validation + feature profiling]--> baseline.json
                                                        |
current.csv ----[schema + missingness + type checks]----+--> [PSI/JSD + optional accuracy]
                                                               |
                                                       [threshold decision]
                                                         /           \
                                                    report.json     report.html
                                                         \           /
                                                         CLI exit 0 / 2
```

`src/trainserve_sentinel/core.py`: CSV parsing, baseline, metrics and policy. `report.py`: escaped static HTML. `cli.py`: CLI, atomic outputs, exit codes. `scripts_generate.py`: deterministic synthetic fixtures. `tests/`: regression and CLI tests. `.github/workflows/ci.yml`: source-level CI.

## Metrics and caveats

PSI is calculated as `sum((p_i-q_i)*ln(p_i/q_i))` over five baseline-quantile bins, with 0.5-count smoothing. Baseline bin edges are fixed; they are *not* re-fit on current data. Constant numeric features use a separate change-rate check. JSD is symmetric, bounded 0..1 (base-2 logarithm). Missing values are excluded from distribution comparisons and evaluated separately.

These are heuristic alert thresholds, not p-values or statistically calibrated guarantees. Tiny batches are inconclusive. Baseline observed min/max are **not** valid-domain constraints; out-of-range is a heuristic. Drift does not establish model performance degradation, nor does no drift prove quality. Accuracy monitoring only works with delayed ground-truth labels supplied. Inference is batch-only and in-memory (max 200,000 rows, 200 columns), not a production streaming monitor. The default missing markers (`NA`, `null`, etc.) can be real categories in some domains; adjust source data accordingly. CSVs may contain sensitive information: avoid uploading raw data to GitHub.

## Project status and evidence

See `docs/RESEARCH.md`, `docs/ARCHITECTURE.md`, `docs/VERIFICATION.md`, and `docs/PROJECT_CHECKPOINT.md`. All sample rows are synthetic and deterministic. No external model, API, paid account or cloud deployment is required.

## License
MIT.
