import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import wiki


class WikiTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        root_patch = patch.object(wiki, "ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        self.git("init", "-q")
        self.write(wiki.EVIDENCE, "[]")

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)

    def write(self, path, content):
        path = self.root / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def record(self, source):
        return {
            "page": "topic/page.md", "claim": "A dated claim.", "applies_to": "Test version",
            "checked_on": "2000-01-01", "source": source,
        }

    def test_heading_numbers_and_fences(self):
        path = Path("topic/page.md")
        lines = ["## 2. First", "```md", "## 25. Example", "[missing](lost.md)", "```", "~~~sql"]
        self.assertEqual(
            [(item["line"], item["code"]) for item in wiki.check_markdown(path, lines)],
            [(1, "heading-number"), (6, "unclosed-fence")],
        )

    def test_links_resolve_spaces_and_ignore_code(self):
        self.write("topic/with spaces.md", "# Target")
        lines = [
            "[exists](<with spaces.md>)", "[encoded](with%20spaces.md#section)",
            "`[example](absent.md)`", "[outside](../../outside.md)", "[missing](absent.md)",
        ]
        issues = wiki.check_markdown(Path("topic/page.md"), lines)
        self.assertEqual([item["line"] for item in issues], [4, 5])

    def test_changed_scope_covers_staged_and_untracked_markdown(self):
        self.write("topic/staged.md", "# Staged")
        self.git("add", "topic/staged.md")
        self.write("topic/new.md", "# New")
        self.write("other/other.md", "# Other")
        self.assertEqual(
            wiki.markdown_paths(Path("topic"), changed=True),
            [Path("topic/new.md"), Path("topic/staged.md")],
        )

    def test_external_record_reports_due_and_detects_claim_edits(self):
        page = self.write("topic/page.md", "A dated claim.\n")
        record = self.record({"url": "https://example.org/docs", "locator": "Section 1"})
        self.write(wiki.EVIDENCE, json.dumps([record]))
        result = wiki.inspect(Path("topic"), max_age=90)
        self.assertEqual(result["pages_with_evidence"], 1)
        self.assertEqual(len(result["due_for_recheck"]), 1)
        page.write_text("Changed claim.\n", encoding="utf-8")
        result = wiki.inspect(Path("topic"))
        self.assertEqual(result["pages_with_evidence"], 0)
        self.assertEqual(result["issues"][0]["code"], "evidence")

    def test_source_only_change_detects_drift_for_citing_page(self):
        self.write("topic/page.md", "A dated claim.\n")
        self.write("sources/source.txt", "First line\nOriginal text\n")
        record = self.record({"path": "sources/source.txt", "start": 2, "end": 2, "quote": "Original text"})
        self.write(wiki.EVIDENCE, json.dumps([record]))
        self.git("add", ".")
        self.assertEqual(wiki.inspect(Path("topic"))["issues"], [])
        self.write("sources/source.txt", "First line\nRevised text\n")
        result = wiki.inspect(Path("sources"), changed=True)
        self.assertIn("Local source excerpt changed", result["issues"][0]["message"])

    def test_malformed_source_url_is_reported_as_evidence_issue(self):
        self.write("topic/page.md", "A dated claim.\n")
        self.write(wiki.EVIDENCE, json.dumps([self.record({"url": 123})]))
        issues = wiki.inspect(Path("topic"))["issues"]
        self.assertEqual([item["code"] for item in issues], ["evidence"])

    def test_required_evidence_applies_to_changed_prose_not_other_claims(self):
        page = Path("topic/page.md")
        self.write(page, "# Old title\n\nA dated claim.\nOriginal behavior.\n")
        self.git("add", str(page))
        self.git("-c", "user.name=Wiki Test", "-c", "user.email=wiki@example.org",
                 "-c", "commit.gpgsign=false", "commit", "-qm", "Add original page")
        record = self.record({"url": "https://example.org/docs", "locator": "Section 1"})
        self.write(wiki.EVIDENCE, json.dumps([record]))
        self.write(page, "# New title\n\nA dated claim.\nUpdated behavior.\n```text\nExample\n```\n")
        command = ["wiki.py", "check", "--scope", str(page), "--require-evidence", "--json"]

        def check():
            output = io.StringIO()
            with patch.object(sys, "argv", command), contextlib.redirect_stdout(output):
                status = wiki.main()
            return status, json.loads(output.getvalue())["issues"]

        status, issues = check()
        self.assertEqual(status, 1)
        self.assertEqual([(item["line"], item["code"]) for item in issues], [(4, "missing-evidence")])

        self.write(wiki.EVIDENCE, json.dumps([record, dict(record, claim="Updated behavior.")]))
        self.assertEqual(check(), (0, []))

    def test_required_evidence_checks_untracked_pages(self):
        page = Path("topic/page.md")
        self.write(page, "# New page\n\nNew behavior.\n")
        command = ["wiki.py", "check", "--scope", str(page), "--require-evidence", "--json"]
        output = io.StringIO()
        with patch.object(sys, "argv", command), contextlib.redirect_stdout(output):
            self.assertEqual(wiki.main(), 1)
        issues = json.loads(output.getvalue())["issues"]
        self.assertEqual([(item["line"], item["code"]) for item in issues], [(3, "missing-evidence")])

    def test_review_preview_is_scoped_and_excludes_untracked_by_default(self):
        self.write("topic/staged.md", "# Staged")
        self.write("other/other.md", "# Other")
        self.git("add", "topic/staged.md", "other/other.md")
        self.write("topic/new.md", "# New")
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(wiki.subprocess, "Popen", wraps=subprocess.Popen) as process:
            self.assertEqual(wiki.review(Path("topic"), preview=True, include_untracked=False), 0)
        self.assertEqual(output.getvalue().splitlines()[1:], ["topic/staged.md"])
        self.assertTrue(all(call.args[0][0] == "git" for call in process.call_args_list))

    def test_review_treats_agent_error_as_failure_even_with_zero_exit(self):
        self.write("topic/staged.md", "# Staged")
        self.git("add", "topic/staged.md")
        fake = self.write("bin/coderabbit", "#!/bin/sh\nprintf '%s\\n' '{\"type\":\"error\"}'\n")
        fake.chmod(0o755)
        with patch.dict(os.environ, {"PATH": f"{fake.parent}{os.pathsep}{os.environ['PATH']}"}):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(wiki.review(Path("topic"), preview=False, include_untracked=False), 1)

    def test_stop_hook_warns_without_requesting_continuation(self):
        self.write("topic/page.md", "## 3. Wrong start\n")
        payload = {"hook_event_name": "Stop", "stop_hook_active": False}
        output = io.StringIO()
        with patch.object(sys, "stdin", io.StringIO(json.dumps(payload))), contextlib.redirect_stdout(output):
            self.assertEqual(wiki.stop_hook(), 0)
        self.assertEqual(set(json.loads(output.getvalue())), {"systemMessage"})


if __name__ == "__main__":
    unittest.main()
