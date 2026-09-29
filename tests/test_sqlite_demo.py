import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from examples.sqlite_acl_demo import create_database, retrieve_case, sync_permissions
from rag_scope_check.core import evaluate


ROOT = Path(__file__).resolve().parents[1]
LIMITS = {"min_cohort_recall": 0.8, "max_underfill_rate": 0}


class PermissionSyncDemoTests(unittest.TestCase):
    def test_sync_restores_recall_without_changing_source_or_labels(self):
        with closing(create_database()) as db:
            tables = ("source_permissions", "documents", "search_index")
            before = {table: db.execute(f"SELECT * FROM {table}").fetchall() for table in tables}
            stale = retrieve_case(db)
            sync_permissions(db)
            corrected = retrieve_case(db)
            for table in tables:
                self.assertEqual(db.execute(f"SELECT * FROM {table}").fetchall(), before[table])
            self.assertEqual(
                db.execute("SELECT * FROM index_permissions ORDER BY principal, doc_id").fetchall(),
                db.execute("SELECT * FROM source_permissions ORDER BY principal, doc_id").fetchall(),
            )

        for field in ("id", "tenant", "cohort", "k", "eligible_doc_count",
                      "authorized_doc_ids", "relevant_doc_ids"):
            self.assertEqual(stale[field], corrected[field], field)
        self.assertEqual(stale["returned_doc_ids"], ["handbook"])
        self.assertEqual(set(corrected["returned_doc_ids"]), {"handbook", "policy-v3"})
        for case, verdict, recall, underfill in (
            (stale, "FAIL", 0, True), (corrected, "PASS", 1, False),
        ):
            report = evaluate([case], **LIMITS)
            self.assertEqual(report["verdict"], verdict)
            result = report["cases"][0]
            self.assertEqual(result["authorized_recall"], recall)
            self.assertEqual(result["candidate_underfill"], underfill)
            self.assertEqual(result["underfilled_top_k"], underfill)
            self.assertEqual(result["leaked_doc_ids"], [])
            self.assertEqual(result["unauthorized_candidate_ids"], [])

    def test_exported_cases_gate_through_cli_with_identical_thresholds(self):
        with tempfile.TemporaryDirectory() as directory:
            for flags, exit_code in (([], 1), (["--sync-permissions"], 0)):
                with self.subTest(flags=flags):
                    demo = subprocess.run(
                        [sys.executable, "examples/sqlite_acl_demo.py", *flags],
                        cwd=ROOT, capture_output=True, text=True, check=True,
                    )
                    evidence = Path(directory) / "case.jsonl"
                    evidence.write_text(demo.stdout, encoding="utf-8")
                    gate = subprocess.run(
                        [sys.executable, "-m", "rag_scope_check", str(evidence),
                         "--min-cohort-recall", "0.8", "--max-underfill-rate", "0",
                         "--format", "json"],
                        cwd=ROOT, capture_output=True, text=True,
                    )
                    self.assertEqual(gate.returncode, exit_code, gate.stderr)
                    report = json.loads(gate.stdout)
                    self.assertEqual(report["case_count"], 1)
                    self.assertEqual(report["verdict"], "FAIL" if exit_code else "PASS")
                    self.assertEqual(report["cases"][0]["leaked_doc_ids"], [])
                    self.assertEqual(report["failures"], [
                        "acme/finance: authorized recall below 0.8 or unscored",
                        "acme/finance: underfill rate above 0",
                    ] if exit_code else [])


if __name__ == "__main__":
    unittest.main()
