import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import evaluate
import wiki


class EvaluationTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name).resolve()
        fixture_root = patch.object(wiki, "ROOT", root)
        fixture_root.start()
        self.addCleanup(fixture_root.stop)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        self.page = root / "topic" / "source.md"
        self.page.parent.mkdir()
        self.page.write_text("# Source\nThe factory key locates the connection holder.\n", encoding="utf-8")
        self.case = {
            "id": "binding", "question": "How is the connection found?",
            "query": "factory key", "scope": "topic",
            "expected_pages": ["topic/source.md"],
            "facts": [["factory key", "connection holder"]],
        }
        self.answer = {
            "status": "answered", "answer": "The factory key locates the connection holder.",
            "citations": [{"path": "topic/source.md", "line": 2,
                           "quote": "The factory key locates the connection holder."}],
        }

    def run_case(self, answers=None, case=None, top_k=5):
        return evaluate.run_cases([case or self.case], top_k, answers)[0]

    def test_local_search_supplies_a_verifiable_excerpt(self):
        result = self.run_case()
        self.assertEqual(result["failures"], {})
        self.assertEqual(result["rank"], 1)

    def test_top_k_counts_distinct_documents(self):
        (self.page.parent / "earlier.md").write_text("factory key\nfactory key\n", encoding="utf-8")
        self.assertEqual(self.run_case(top_k=2)["rank"], 2)
        self.assertIn("search", self.run_case(top_k=1)["failures"])

    def test_valid_location_with_incorrect_quote_fails(self):
        self.answer["citations"][0]["quote"] += " Invented."
        self.assertIn("citation", self.run_case({"binding": self.answer})["failures"])

    def test_a_real_but_unrelated_line_cannot_support_the_answer(self):
        self.answer["citations"] = [{"path": "topic/source.md", "line": 1, "quote": "# Source"}]
        self.assertIn("support", self.run_case({"binding": self.answer})["failures"])

    def test_answer_must_explain_expected_fact(self):
        self.answer["answer"] = "I found an answer."
        self.assertIn("answer", self.run_case({"binding": self.answer})["failures"])

    def test_missing_answer_is_reported(self):
        self.assertIn("answer", self.run_case({})["failures"])

    def test_refusal_case_requires_abstention_without_a_citation(self):
        case = dict(self.case, query="nothing matches", expected_pages=[], facts=[])
        self.assertEqual(self.run_case(case=case)["failures"], {})
        self.assertIn("answer", self.run_case({"binding": self.answer}, case)["failures"])

    def test_report_diff_lists_new_resolved_and_persistent_failures(self):
        def report(failures):
            return {
                "schema_version": 1, "dataset_sha256": "dataset", "top_k": 5, "mode": "external",
                "cases": [{"id": "binding", "question": "Q", "failures": failures}],
            }
        before = report({"search": ["missing"], "answer": ["wrong"]})
        after = report({"search": ["still missing"], "support": ["unsupported"]})
        changes = evaluate.compare(before, after)[0]
        self.assertEqual(changes["new"], {"support": ["unsupported"]})
        self.assertEqual(changes["resolved"], {"answer": ["wrong"]})
        self.assertEqual(changes["persistent"], {"search": ["still missing"]})
        with self.assertRaises(ValueError):
            evaluate.compare(before, dict(after, top_k=3))

    def test_question_sheet_omits_expected_results(self):
        sheet = evaluate.questions([self.case])
        self.assertNotIn("facts", json.dumps(sheet))
        self.assertNotIn("expected_pages", json.dumps(sheet))
