"""Static HTML report; escaped values, no third-party assets or raw rows."""
from __future__ import annotations

import html
from typing import Any


def render_html(report: dict[str, Any]) -> str:
    escape = lambda v: html.escape(str(v), quote=True)
    rows = "\n".join(
        "<tr><td>{}</td><td>{}</td><td><span class='tag {}'>{}</span></td><td>{}</td><td>{}</td></tr>".format(
            escape(f["feature"]), escape(f["check"]), escape(f["status"]),
            escape(f["status"].upper()), escape(f["value"] if f["value"] is not None else "-"),
            escape(f["message"]))
        for f in report["findings"]
    )
    return f"""<!doctype html>
<html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>TrainServe Sentinel | {escape(report['overall'].upper())}</title>
<style>
:root{{--bg:#0b1324;--panel:#14213b;--text:#e9f0fb;--muted:#aebed3;--line:#324561;--ok:#b4e5c3;--warn:#ffe0a0;--bad:#ffb8bd}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,sans-serif}}
main{{max-width:1080px;margin:35px auto;padding:0 20px}}header{{padding:28px;background:var(--panel);border-radius:18px}}
h1{{font-size:29px;margin:0 0 6px}}p{{color:var(--muted)}}.summary{{display:flex;gap:16px;flex-wrap:wrap;margin-top:16px}}
.stat{{padding:12px 18px;background:#1e3050;border-radius:12px;min-width:130px}}.stat strong{{display:block;font-size:20px}}
section{{margin-top:25px;overflow:auto}}table{{border-collapse:collapse;width:100%;background:var(--panel);border-radius:12px;overflow:hidden}}
th,td{{text-align:left;padding:12px;border-bottom:1px solid var(--line);vertical-align:top}}th{{color:var(--muted);font-weight:600}}
.tag{{padding:4px 9px;border-radius:6px;font-weight:700;font-size:12px}}.pass{{background:#254b3e;color:var(--ok)}}
.warn{{background:#514026;color:var(--warn)}}.fail,.inconclusive{{background:#592c3b;color:var(--bad)}}
footer{{margin:24px 0;color:var(--muted)}}
</style></head><body><main><header><h1>TrainServe Sentinel</h1>
<p>Offline ML input monitoring. Baseline: <b>{escape(report['baseline_source'])}</b> | Current: <b>{escape(report['current_source'])}</b></p>
<div class='summary'><div class='stat'>Decision<strong>{escape(report['overall'].upper())}</strong></div>
<div class='stat'>Baseline rows<strong>{escape(report['baseline_rows'])}</strong></div>
<div class='stat'>Current rows<strong>{escape(report['current_rows'])}</strong></div>
<div class='stat'>Findings<strong>{len(report['findings'])}</strong></div></div></header>
<section><h2>Checks and evidence</h2><table><thead><tr><th>Feature</th><th>Check</th><th>Result</th><th>Value</th><th>Interpretation</th></tr></thead><tbody>{rows}</tbody></table></section>
<footer>Metrics are heuristics. PSI/JSD thresholds are configurable, not p-values. No raw CSV records are embedded. 
Drift alone does not establish model degradation.</footer></main></body></html>"""
