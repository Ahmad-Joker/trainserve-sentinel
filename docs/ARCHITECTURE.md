# Architecture and design decisions

- **Trust boundary:** local CSV files are untrusted input; parser rejects duplicate/blank headers, ragged rows, non-UTF-8 content, empty batches, >200k rows and >200 columns. Baseline JSON is versioned and validated. HTML escapes all user-sourced strings.
- **Baseline:** freeze reference schema and per-feature type, missing rate, numeric quantile edges/counts or categorical counts; optionally labeled classification accuracy. This is a contract snapshot, not a fitted predictive model.
- **Current batch:** do not learn or update the baseline from current data. Separate missingness from distribution checks; report numeric coercion failures and schema mismatches.
- **Drift metrics:** PSI with baseline quantile bins and 0.5-count smoothing; JSD with base-2 logs. Heuristics are sensitive to sample size and baseline representativeness; thresholds must be calibrated for domain data.
- **Policy:** fail / inconclusive / warn / pass priority. Exit 2 for fail or inconclusive, 0 for pass/warn, 1 for malformed input. Explicit error codes make it suitable for CI gates.
- **Outputs:** JSON for automation, escaped self-contained HTML for humans, both written via temporary file then atomic replace. No raw data rows in output.
- **Optional labels:** compares paired classification labels and predictions if available; missing or too few labeled rows are inconclusive rather than silently assuming model quality.
- **Scope:** one local batch at a time. No scheduler, webhook, database, live model, auth or cloud deployment. Not a replacement for Evidently, GX or whylogs.
