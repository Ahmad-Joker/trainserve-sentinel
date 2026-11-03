# Research and project choice (2026-11-03)

## Evidence from employers (official listings; links checked 2026-11-03)
- [Amazon 2027 Software Dev Engineer Intern (Machine Learning), UK](https://www.amazon.jobs/en/jobs/10588762/2027-software-dev-engineer-intern-machine-learning-uk): programming, systems, databases, cloud and communicating technical decisions. Internship eligibility depends on applicant's study dates.
- [Graphcore Cloud Platform Summer Intern 2027](https://job-boards.greenhouse.io/graphcore/jobs/8894965002): deploy, test and monitor AI-supporting services; deadline 29 November 2026; Bristol, UK.
- [Graphcore Graduate Software Engineer, AI/ML Test Systems 2027](https://job-boards.greenhouse.io/graphcore/jobs/8894364002): numerical accuracy, performance analysis and test infrastructure; Bristol, UK.
- [Sprinto AI Implementation Intern](https://jobs.lever.co/Sprinto/6dfd5f41-57b6-40e8-9eab-ba4083c1a7c4): Python, data pipelines, model evaluation and AI infrastructure.
- [Firework Data Engineer Intern](https://jobs.lever.co/fireworkhq/36722fbd-2705-4beb-83aa-1884068eaa09): Python/SQL, ETL, data pipelines and quality.
- [Scale AI Software Engineering Intern (Summer 2027)](https://job-boards.greenhouse.io/scaleai/jobs/4730846005): full-stack/data infrastructure and shipped projects. Check graduation-date eligibility; listing says Fall 2027/Spring 2028.

These are evidence of job requirements, **not** guarantees that any role is open to a candidate in Egypt, remote, or eligible. The current accessible CV (Nov 1 DotPy version) says expected graduation 2028, whereas earlier application records may differ. Eligibility must be verified for each application.

## Existing tools and differentiation
- [Evidently OSS](https://www.evidentlyai.com/evidently-oss): full-featured data/ML/LLM evaluation and monitoring. TrainServe Sentinel is not a competitor on breadth; it focuses on a transparent, dependency-free CSV-to-CI teaching exercise.
- [Great Expectations](https://docs.greatexpectations.io/docs/reference/learn/data_quality_use_cases/schema/): declarative schema and data quality expectations. This project additionally calculates fixed-baseline drift heuristics.
- [whylogs](https://github.com/whylabs/whylogs): profiles for data quality and drift at scale. This project does not claim scalable telemetry or privacy-preserving distributed profiling.

## Portfolio gap
Ahmad's CV shows ML modeling, RAG/agents, guarded workflows, FastAPI, CI and data profiling. The next useful distinction is **train/serve input validation + drift metrics + CI policy gates** with explicit failure modes and readable reporting. The prior Outbox Reliability Lab covers message processing and retries, so repeating it is avoided.

## Ranked shortlist (editorial, not a hiring probability)
Weights: hiring evidence 30, skill-gap coverage 25, utility 15, differentiation 10, feasible local MVP 15, cost 5. Each category is 0..weight.

| Rank | Project | Hiring | Gap | Utility | Different | Feasible | Cost | Total |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | **TrainServe Sentinel: CSV drift + quality CI gate** | 27 | 24 | 14 | 8 | 15 | 5 | **93** |
| 2 | SQL Lineage Contract Checker | 26 | 20 | 14 | 9 | 14 | 5 | **88** |
| 3 | EdgeVision Failure Slice Evaluator | 25 | 23 | 13 | 9 | 11 | 5 | **86** |
| 4 | Distributed Feature Store Emulator | 26 | 24 | 13 | 9 | 7 | 3 | **82** |
| 5 | LLM Retrieval Regression Bench | 28 | 15 | 14 | 5 | 15 | 4 | **81** |

Sorted by total: 1 TrainServe (93), 2 SQL Lineage (88), 3 EdgeVision (86), 4 Distributed Feature Store (82), 5 Retrieval Bench (81). Totals are subjective feasibility-weighted decisions, not measured employer demand. Selected TrainServe because it fills a concrete gap, has a demonstrable user flow, and can be fully verified offline.
