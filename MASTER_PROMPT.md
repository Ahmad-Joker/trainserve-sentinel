# Implementation master prompt — TrainServe Sentinel

Date: 2026-11-03. Owner: Ahmad Essam Abdelaziz. This prompt precedes the implementation.

## Problem and audience
Data scientists and junior ML platform engineers often have a trained model and a reference CSV but no cheap way to catch changed inference inputs before they silently degrade predictions. Build an offline, reproducible, explainable **batch train/serve monitoring gate**, not another model trainer, chatbot, or general observability platform.

## Hiring evidence and project selection
Official postings reviewed on 2026-11-03: Amazon 2027 SDE/ML UK (Python, systems, databases, engineering), Graphcore Cloud Platform Summer Intern 2027 (deploy/test/monitor), Graphcore Graduate AI/ML Test Systems 2027 (accuracy/performance test infrastructure), Sprinto AI Implementation Intern (data pipelines/evaluation), Firework Data Engineer Intern (Python, SQL, ETL, quality), Scale AI Software Engineering Intern Summer 2027 (AI infrastructure and data products). Source links in docs/RESEARCH.md. Ahmad's Nov 1 CV and GitHub portfolio already include RAG, guardrails, API and job reliability, so this project should demonstrate a distinct ML data-quality and drift-validation capability. Distinguish editorial fit scores from measured employment outcomes.

## MVP boundary and users
CLI tool for local CSV batches with Python >=3.10 standard library only. User can (1) profile a baseline CSV and save a versioned JSON contract, (2) scan a current CSV against it, (3) receive JSON + self-contained HTML findings with explicit per-feature metrics and CI-friendly exit codes, (4) optionally compare classification accuracy if ground-truth and predicted-label columns are present in both CSVs, (5) use deterministic sample data and tests. No live model, streaming, external services, alerts, cloud deployment, or claims of statistical significance.

## Acceptance criteria
- `python -m trainserve_sentinel baseline --csv samples/baseline.csv --out artifacts/baseline.json --ignore label,prediction --label label --prediction prediction` produces a versioned, human-readable baseline.
- `python -m trainserve_sentinel scan --baseline artifacts/baseline.json --csv samples/clean.csv --json artifacts/clean.json --html artifacts/clean.html` returns 0 for a healthy batch.
- The shifted sample returns exit 2 and an actionable failure report (at least one drift and/or data-quality failure).
- Empty or malformed inputs, invalid policy, duplicate headers, missing required columns, type coercion, non-finite numeric values, unknown categories, tiny samples, zero-variance numeric columns and escaped HTML handled intentionally.
- PSI for numeric distributions uses baseline-derived fixed quantile edges and Laplace-smoothed bin proportions; categorical JSD is bounded [0,1] using base-2 logarithms. Explain limitations of thresholds, small samples and independence assumptions.
- Optional accuracy decline computed only with paired label/prediction fields and enough labeled rows; otherwise marked unavailable or inconclusive, never assumed passed.
- Tests include unit, integration, CLI return codes and HTML escaping. Generate reproducible fixture CSVs. Test on actual local Python, run compile and end-to-end CLI smoke, fix observed errors. Never fabricate CI or Docker outcomes.
- Include README, architecture, evidence, research, CI, reproducible setup and explanatory PDF.

## Architecture / data flow
CSV reader -> schema + type validation -> baseline profile JSON (version 1) -> current batch scanner -> data quality checks + numeric PSI + categorical JSD + optional accuracy delta -> policy decision (pass/warn/fail/inconclusive) -> JSON and escaped static HTML -> CLI exit 0/2 (1 for input/tool error).

## Implementation sequence
1. Define strict dataclasses/config, CSV parsing and safe serialization.
2. Implement deterministic numeric quantile bins, PSI, categorical JSD, missingness, schema checks and optional accuracy.
3. Implement CLI baseline/scan, atomic outputs and readable errors.
4. Build escaped HTML report, reproducible samples, documentation and CI workflow.
5. Add targeted tests, run them, run smoke on clean and shifted fixtures, inspect report, fix regressions.
6. Save source + PDF in Library; check GitHub account and dedicated repo slug `Ahmad-Joker/trainserve-sentinel`; create only if authenticated tool supports creation; push fresh branch and open PR without merging. If repo creation is unavailable, do not place code in another repo; preserve source and record exact blocker.

## Operational and ethical constraints
No purchases, credentials, PII, hidden dependencies or invented production performance. Keep inputs local. Report thresholds as heuristics, not hypothesis-test p-values. Avoid falsely equating drift with model failure. Do not expose raw records in reports. Never overwrite existing unrelated repositories.

## PDF requirements
Create readable PDF explaining user problem, shortlist and weighted scoring, cited job evidence, code architecture, examples, actual tests, run instructions, limitations, honest CV bullet, interview pitch and publication status. Verify rendered pages. Save PDF and source ZIP durably and link both in task response.

## Loop and completion definition
Implement -> run tests -> inspect failures -> smallest fix -> rerun relevant tests -> smoke -> inspect outputs. A local MVP is complete only after real verification; publication is complete only with confirmed remote branch, commit, and PR. If blocked, checkpoint partial status and continue on later run rather than inventing success or duplicating a project.
