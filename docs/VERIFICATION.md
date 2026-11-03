# Verification record — 2026-11-03

This project was built and tested locally on Linux with Python 3.13 and the Python standard library. Synthetic fixtures are generated deterministically by `scripts_generate.py` (seed 20261103). Original findings are preserved below; see the publication section for later GitHub checks.

## Local checks verified
- `python -m compileall -q src tests` — passed.
- `PYTHONPATH=src python -m unittest discover -s tests -v` — 34/34 tests passed. On the publication attempt a second independent extracted-archive run of `PYTHONPATH=src python -m pytest -q` also passed all 34.
- Baseline CLI — produced 180 rows, three features and optional label/prediction statistics.
- Clean scan — PASS, 10 checks, exit code 0.
- Intentionally shifted scan — FAIL, 8 failure checks, exit code 2 as designed.
- Shifted checks: age PSI 4.587793; income PSI 2.538644; channel JSD 0.697908; unseen-category rate 0.5; income missingness increase 0.2; accuracy drop 0.25; age out-of-baseline-range 0.8; income out-of-baseline-range 0.680556.
- Self-contained HTML outputs escape untrusted content and do not include raw input rows.

## Defects found and fixed during original build
1. Tiny sample handling: suppress unstable distribution metrics while preserving schema/type checks; report INCONCLUSIVE and exit 2.
2. Reject malformed baseline performance data and inconsistent histogram totals.
3. Prevent output files from overwriting source inputs or each other.
4. The initially isolated editable-install venv lacked setuptools.build_meta. The original run made the preinstalled build backend visible and confirmed editable CLI installation without fetching dependencies.

## Publication transfer verification
- Dedicated GitHub repo: `Ahmad-Joker/trainserve-sentinel`; feature branch `feat/trainserve-sentinel-mvp` based on the existing `main`.
- Saved ZIP recovered and checked against its separately saved explanatory PDF.
- The Python source, tests, metadata, CI workflow and all three synthetic samples were transferred through GitHub Git objects. Their Git blob hashes were compared with the saved archive; an initial transfer typo in one Python dictionary lookup was corrected **before** publication and the resulting source blob matched the saved archive.
- GitHub Actions and pull-request status are tracked on the PR; local test results must not be mistaken for CI results.

## Limitations
- Batch-only, in-memory CSV monitor; no scheduler, live inference, streaming, cloud deployment, Docker runtime, statistical calibration or production security review.
- Drift heuristics are not statistical p-values and cannot prove model performance degradation.
- Live workloads, false-positive alert rates and actual employment impact have not been measured.
