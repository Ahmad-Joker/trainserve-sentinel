import csv
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from trainserve_sentinel.core import (
    DataError, _jsd, _psi, build_baseline, number, read_csv,
    scan, validate_baseline, validate_policy,
)
from trainserve_sentinel.report import render_html

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "samples/baseline.csv"
CLEAN = ROOT / "samples/clean.csv"
SHIFT = ROOT / "samples/shifted.csv"


def fixture(tmp, header, rows):
    p = Path(tmp) / "input.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    return p


class CSVTests(unittest.TestCase):
    def test_bom_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bom.csv"
            p.write_text("\ufeffage,city\n23,Alex\n", encoding="utf-8")
            self.assertEqual(read_csv(p)[0], ["age", "city"])

    def test_duplicate_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(DataError, "duplicate"):
                read_csv(fixture(tmp, ["a", "a"], [[1, 2]]))

    def test_ragged_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(DataError, "row 2"):
                read_csv(fixture(tmp, ["a", "b"], [[1]]))

    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "empty.csv"
            p.write_text("", encoding="utf-8")
            with self.assertRaises(DataError):
                read_csv(p)

    def test_numeric_invalid_nonfinite(self):
        self.assertIsNone(number("inf"))
        self.assertIsNone(number("NaN"))
        self.assertIsNone(number("oops"))
        self.assertEqual(number(" 3.5 "), 3.5)


class StatsTests(unittest.TestCase):
    def test_psi_identical(self):
        self.assertAlmostEqual(_psi([10, 20, 30], [10, 20, 30]), 0)

    def test_psi_shifted(self):
        self.assertGreater(_psi([10, 20, 30], [30, 20, 10]), 0.1)

    def test_js_identical(self):
        self.assertAlmostEqual(_jsd({"a": 5, "b": 5}, {"a": 5, "b": 5}), 0)

    def test_js_disjoint(self):
        self.assertAlmostEqual(_jsd({"a": 10}, {"b": 10}), 1)

    def test_js_symmetry(self):
        a, b = {"a": 7, "b": 3}, {"a": 1, "c": 9}
        self.assertAlmostEqual(_jsd(a, b), _jsd(b, a))

    def test_policy_rejects_unknown(self):
        with self.assertRaises(DataError):
            validate_policy({"foo": 2})

    def test_policy_rejects_inverted(self):
        with self.assertRaises(DataError):
            validate_policy({"numeric_psi_warn": 0.5, "numeric_psi_fail": 0.2})

    def test_policy_rejects_nan(self):
        with self.assertRaises(DataError):
            validate_policy({"numeric_psi_fail": float("nan")})


class BaselineScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = build_baseline(BASE, label="label", prediction="prediction")

    def test_baseline_three_features(self):
        self.assertEqual(set(self.baseline["features"]), {"age", "income", "channel"})
        self.assertEqual(self.baseline["rows"], 180)

    def test_clean_pass(self):
        result = scan(self.baseline, CLEAN)
        self.assertEqual(result["overall"], "pass")
        self.assertTrue(all(f["status"] == "pass" for f in result["findings"]))

    def test_shift_fail(self):
        result = scan(self.baseline, SHIFT)
        self.assertEqual(result["overall"], "fail")
        self.assertIn("numeric_psi", {f["check"] for f in result["findings"] if f["status"] == "fail"})
        self.assertIn("unknown_category_rate", {f["check"] for f in result["findings"] if f["status"] == "fail"})

    def test_missing_feature(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = fixture(tmp, ["age", "income"], [[25, 30000]] * 35)
            result = scan(self.baseline, p)
            self.assertIn("schema_missing", {f["check"] for f in result["findings"]})
            self.assertEqual(result["overall"], "fail")

    def test_numeric_type_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = fixture(tmp, ["age", "income", "channel"], [["oops", 40000, "organic"]] * 35)
            self.assertIn("numeric_type_errors", {f["check"] for f in scan(self.baseline, p)["findings"]})

    def test_tiny_sample_inconclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = fixture(tmp, ["age", "income", "channel"], [[25, 40000, "organic"]])
            self.assertEqual(scan(self.baseline, p)["overall"], "inconclusive")

    def test_constant_baseline_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = fixture(tmp, ["x", "channel"], [[5, "a"]] * 60)
            base = build_baseline(p)
            p2 = Path(tmp) / "changed.csv"
            with p2.open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["x", "channel"])
                writer.writerows([[8, "a"]] * 60)
            result = scan(base, p2)
            self.assertTrue(any(f["check"] == "constant_changed" and f["status"] == "fail" for f in result["findings"]))

    def test_all_missing_baseline_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = fixture(tmp, ["a"], [[""]] * 50)
            with self.assertRaisesRegex(DataError, "only missing"):
                build_baseline(p)

    def test_invalid_baseline_version(self):
        with self.assertRaises(DataError):
            validate_baseline({"version": 999})

    def test_html_escapes_malicious_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = fixture(tmp, ["<script>alert(1)</script>"], [["x"]] * 50)
            base = build_baseline(p)
            result = scan(base, p)
            html = render_html(result)
            self.assertIn("&lt;script&gt;", html)
            self.assertNotIn("<script>alert(1)</script>", html)

    def test_optional_accuracy_drop(self):
        result = scan(self.baseline, SHIFT)
        acc = [f for f in result["findings"] if f["check"] == "accuracy_drop"]
        self.assertEqual(len(acc), 1)
        self.assertGreater(acc[0]["value"], 0.1)

    def test_missing_performance_inconclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = fixture(tmp, ["age", "income", "channel"], [[30, 30000, "organic"]] * 50)
            result = scan(self.baseline, p)
            self.assertTrue(any(f["feature"] == "__performance__" and f["status"] == "inconclusive" for f in result["findings"]))

    def test_baseline_roundtrip(self):
        restored = json.loads(json.dumps(self.baseline))
        self.assertEqual(scan(restored, CLEAN)["overall"], "pass")


class CLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-m", "trainserve_sentinel", *map(str, args)],
                              capture_output=True, text=True, cwd=ROOT)

    def test_cli_clean_and_shift(self):
        with tempfile.TemporaryDirectory() as tmp:
            baseline = Path(tmp) / "baseline.json"
            out = Path(tmp) / "report.json"
            html = Path(tmp) / "report.html"
            self.assertEqual(self.run_cli("baseline", "--csv", BASE, "--out", baseline,
                                          "--label", "label", "--prediction", "prediction").returncode, 0)
            self.assertEqual(self.run_cli("scan", "--baseline", baseline, "--csv", CLEAN,
                                          "--json", out, "--html", html).returncode, 0)
            self.assertTrue(html.read_text().startswith("<!doctype html>"))
            self.assertEqual(self.run_cli("scan", "--baseline", baseline, "--csv", SHIFT,
                                          "--json", out, "--html", html).returncode, 2)
            self.assertEqual(json.loads(out.read_text())["overall"], "fail")

    def test_cli_bad_input_code_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self.run_cli("baseline", "--csv", "missing.csv", "--out", Path(tmp) / "out.json")
            self.assertEqual(r.returncode, 1)
            self.assertIn("ERROR", r.stderr)


if __name__ == "__main__":
    unittest.main()

class AdditionalGuardTests(unittest.TestCase):
    def test_corrupt_performance_contract_rejected(self):
        base = build_baseline(BASE, label="label", prediction="prediction")
        base["performance"] = "not an object"
        with self.assertRaises(DataError):
            scan(base, CLEAN)

    def test_corrupt_histogram_rejected(self):
        base = build_baseline(BASE)
        base["features"]["age"]["counts"][0] += 5
        with self.assertRaises(DataError):
            scan(base, CLEAN)

    def test_unknown_policy_file_rejected_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            policy = Path(tmp) / "policy.json"
            policy.write_text('{"unrecognized": 1}', encoding="utf-8")
            proc = subprocess.run([sys.executable, "-m", "trainserve_sentinel", "baseline", "--csv", str(BASE),
                                   "--out", str(Path(tmp) / "baseline.json"), "--policy", str(policy)],
                                  capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("Unknown policy", proc.stderr)

    def test_tiny_batch_with_invalid_numeric_still_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = fixture(tmp, ["age", "income", "channel"], [["bad", 40000, "organic"]])
            base = build_baseline(BASE)
            result = scan(base, p)
            self.assertEqual(result["overall"], "fail")
            self.assertTrue(any(f["check"] == "numeric_type_errors" for f in result["findings"]))

class OutputSafetyTests(unittest.TestCase):
    def test_refuses_overwrite_input_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = fixture(tmp, ["x"], [[1]] * 50)
            original = p.read_bytes()
            proc = subprocess.run([sys.executable, "-m", "trainserve_sentinel", "baseline",
                                   "--csv", str(p), "--out", str(p)],
                                  capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(proc.returncode, 1)
            self.assertEqual(p.read_bytes(), original)

    def test_refuses_json_html_same_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "same.json"
            baseline = Path(tmp) / "baseline.json"
            baseline.write_text(json.dumps(build_baseline(BASE)), encoding="utf-8")
            proc = subprocess.run([sys.executable, "-m", "trainserve_sentinel", "scan",
                                   "--baseline", str(baseline), "--csv", str(CLEAN),
                                   "--json", str(out), "--html", str(out)],
                                  capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(proc.returncode, 1)
            self.assertFalse(out.exists())
