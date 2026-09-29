import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from rag_scope_check.core import InputError, evaluate, evaluate_case, load_cases


ROOT = Path(__file__).resolve().parents[1]


class ScopeCheckTests(unittest.TestCase):
    def test_empty_and_duplicate_batches_fail_closed(self):
        case = load_cases(ROOT / "examples/clean.jsonl")[0]
        for batch, message in (([], "input has no cases"),
                               (iter([]), "input has no cases"),
                               ([case, case], "duplicate case id"),
                               ([None], "each case must be an object")):
            with self.subTest(message=message), self.assertRaisesRegex(InputError, message):
                evaluate(batch)
        self.assertEqual(evaluate(iter([case]))["verdict"], "PASS")

    def test_duplicate_policy_field_is_invalid_in_both_cli_formats(self):
        # A last-key-wins parser changes a denied ID into an allowed one.
        ambiguous = ('{"id":"q","tenant":"t","cohort":"c","k":1,'
                     '"eligible_doc_count":1,"authorized_doc_ids":[],'
                     '"authorized_doc_ids":["secret"],"relevant_doc_ids":[],'
                     '"returned_doc_ids":["secret"]}')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ambiguous.jsonl"
            path.write_text("\n" + ambiguous + "\n", encoding="utf-8")
            with self.assertRaisesRegex(InputError, "line 2: duplicate JSON field"):
                load_cases(path)
            for output_format in ("text", "json"):
                result = subprocess.run(
                    [sys.executable, "-m", "rag_scope_check", str(path),
                     "--format", output_format], cwd=ROOT, capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertIn("line 2: duplicate JSON field 'authorized_doc_ids'", result.stderr)

    def test_authorized_recall_excludes_forbidden_relevant_docs(self):
        case = {
            "id": "q1", "tenant": "acme", "cohort": "finance", "k": 1, "eligible_doc_count": 1,
            "authorized_doc_ids": ["a"], "relevant_doc_ids": ["a", "secret"],
            "returned_doc_ids": ["a"],
        }
        result = evaluate_case(case)
        self.assertEqual(result["authorized_recall"], 1)
        self.assertEqual(result["authorized_relevant_count"], 1)

    def test_leak_fails_even_without_recall_threshold(self):
        report = evaluate(load_cases(ROOT / "examples/regression.jsonl"))
        self.assertEqual(report["verdict"], "FAIL")
        self.assertEqual(report["cases"][0]["leaked_doc_ids"], ["other-tenant-faq"])
        self.assertTrue(report["cases"][0]["candidate_underfill"])
        self.assertEqual(report["cohorts"][0]["underfill_rate"], 0.5)

    def test_missing_relevance_does_not_fake_zero_recall(self):
        case = {
            "id": "q1", "tenant": "acme", "cohort": "guest", "k": 1, "eligible_doc_count": 0,
            "authorized_doc_ids": [], "relevant_doc_ids": ["restricted"],
            "returned_doc_ids": [],
        }
        report = evaluate([case])
        self.assertIsNone(report["cohorts"][0]["mean_authorized_recall"])
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(evaluate([case], min_cohort_recall=0.8)["verdict"], "FAIL")

    def test_policy_freshness_fails_closed_when_requested(self):
        cases = load_cases(ROOT / "examples/clean.jsonl")
        self.assertEqual(evaluate(cases, max_policy_age_hours=1)["verdict"], "PASS")
        without_timestamps = {k: v for k, v in cases[0].items() if k not in ("policy_as_of", "retrieved_at")}
        self.assertEqual(evaluate([without_timestamps], max_policy_age_hours=1)["verdict"], "FAIL")

    def test_invalid_cases_are_rejected(self):
        case = load_cases(ROOT / "examples/clean.jsonl")[0]
        with self.assertRaisesRegex(InputError, "duplicate"):
            evaluate_case({**case, "returned_doc_ids": ["policy-v3", "policy-v3"]})
        with self.assertRaisesRegex(InputError, "come from"):
            evaluate_case({**case, "returned_doc_ids": ["contract"]})
        with self.assertRaisesRegex(InputError, "eligible_doc_count"):
            evaluate_case({**case, "eligible_doc_count": 1})

    def test_tenant_boundary_is_not_hidden_by_shared_cohort_name(self):
        good = load_cases(ROOT / "examples/clean.jsonl")[0]
        bad = {**good, "id": "other-finance", "tenant": "other", "returned_doc_ids": ["handbook"]}
        report = evaluate([good, bad], min_cohort_recall=0.8)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertEqual(len(report["cohorts"]), 2)
        self.assertTrue(any("other/finance" in failure for failure in report["failures"]))

    def test_cli_pass_and_fail_exit_codes(self):
        clean = subprocess.run(
            [sys.executable, "-m", "rag_scope_check", "examples/clean.jsonl",
             "--min-cohort-recall", "1", "--max-underfill-rate", "0"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(clean.returncode, 0, clean.stderr)
        self.assertIn("PASS (2 cases)", clean.stdout)
        regression = subprocess.run(
            [sys.executable, "-m", "rag_scope_check", "examples/regression.jsonl", "--format", "json"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(regression.returncode, 1, regression.stderr)
        self.assertEqual(json.loads(regression.stdout)["verdict"], "FAIL")
        regression_text = subprocess.run(
            [sys.executable, "-m", "rag_scope_check", "examples/regression.jsonl"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertIn("top-k underfilled at candidate generation", regression_text.stdout)
        self.assertIn("unauthorized candidates observed", regression_text.stdout)

    def test_live_sqlite_demo_finds_safe_retrieval_failure(self):
        demo = subprocess.run(
            [sys.executable, "examples/sqlite_acl_demo.py"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
        case = json.loads(demo.stdout)
        report = evaluate([case], min_cohort_recall=0.8, max_underfill_rate=0)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertEqual(report["cases"][0]["leaked_doc_ids"], [])
        self.assertTrue(report["cases"][0]["candidate_underfill"])


if __name__ == "__main__":
    unittest.main()
