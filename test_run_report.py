#!/usr/bin/env python3
"""
Test suite for run_report.py. The mechanical parts (git state, test/eval
counts, ROADMAP.md parsing) must be genuine, not decorative -- these tests
write a scratch ROADMAP.md-shaped file to prove the parser handles wrapped
bullets and multiple sections correctly, and check the real git/test/eval
calls return well-shaped data against this actual repo.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_report as rr


class TestNextRoadmapStep(unittest.TestCase):
    def _with_roadmap(self, text: str):
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
        tmp.write(text)
        tmp.close()
        return patch.object(rr, "ROADMAP_PATH", Path(tmp.name))

    def test_single_line_item(self):
        with self._with_roadmap("## Next\n\n- [ ] Do the thing.\n\n## Backlog\n- [ ] Later.\n"):
            self.assertEqual(rr.next_roadmap_step(), "Do the thing.")

    def test_wrapped_bullet_joined_into_one_line(self):
        text = (
            "## Next\n\n"
            "- [ ] Typed provenance edges. Today Provenance is one flat\n"
            "      record. Add typed EdgeType values and regenerate the\n"
            "      schema.\n\n"
            "## Backlog\n"
        )
        with self._with_roadmap(text):
            step = rr.next_roadmap_step()
        self.assertIn("Typed provenance edges.", step)
        self.assertIn("regenerate the schema.", step)
        self.assertNotIn("\n", step)

    def test_only_reads_the_next_section_not_backlog(self):
        text = "## Next\n\n- [ ] Real next item.\n\n## Backlog\n\n- [ ] Should not be picked.\n"
        with self._with_roadmap(text):
            self.assertEqual(rr.next_roadmap_step(), "Real next item.")

    def test_checked_items_are_skipped(self):
        text = "## Next\n\n- [x] Already done, ignore.\n- [ ] The real next one.\n"
        with self._with_roadmap(text):
            self.assertEqual(rr.next_roadmap_step(), "The real next one.")

    def test_no_next_section_reports_missing(self):
        with self._with_roadmap("## Done\n\n- [x] Everything so far.\n"):
            self.assertIn("no pending item", rr.next_roadmap_step())

    def test_missing_file_reports_missing(self):
        with patch.object(rr, "ROADMAP_PATH", Path("/nonexistent/ROADMAP.md")):
            self.assertIn("no ROADMAP.md found", rr.next_roadmap_step())


class TestRunRstripsOnlyTrailingNewline(unittest.TestCase):
    """Deterministic version of the dotfile-mangling regression, independent
    of this repo's actual git state at test time."""

    def test_leading_space_on_first_line_is_preserved(self):
        fake_result = type("R", (), {"stdout": " M .gitignore\n M README.md\n"})()
        with patch.object(rr.subprocess, "run", return_value=fake_result):
            output = rr._run(["git", "status", "--porcelain"])
        first_line = output.splitlines()[0]
        self.assertEqual(first_line, " M .gitignore")
        self.assertEqual(first_line[3:], ".gitignore")

    def test_trailing_newline_is_removed(self):
        fake_result = type("R", (), {"stdout": "some-branch\n"})()
        with patch.object(rr.subprocess, "run", return_value=fake_result):
            output = rr._run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        self.assertEqual(output, "some-branch")


class TestGitHelpers(unittest.TestCase):
    def test_current_branch_is_nonempty_string(self):
        branch = rr.current_branch()
        self.assertIsInstance(branch, str)
        self.assertNotEqual(branch, "")

    def test_files_changed_returns_a_list_of_strings(self):
        changed = rr.files_changed()
        self.assertIsInstance(changed, list)
        self.assertTrue(all(isinstance(f, str) for f in changed))

    def test_files_changed_surfaces_uncommitted_files_regardless_of_merge_base(self):
        # Deterministic version of the "uncommitted files must surface" case --
        # depending on a real file being uncommitted in the ambient repo state
        # (as an earlier version of this test did, pinned to itself at the
        # moment it was authored) breaks the instant that file gets committed,
        # which isn't a real regression. Mock subprocess.run so this asserts
        # the actual invariant: git status --porcelain output surfaces in
        # files_changed() even when there's no merge-base diff at all.
        def fake_run(cmd, **kwargs):
            if cmd[:2] == ["git", "merge-base"]:
                return type("R", (), {"stdout": ""})()
            if cmd[:2] == ["git", "status"]:
                return type("R", (), {"stdout": " M .gitignore\n?? new_file.py\n"})()
            return type("R", (), {"stdout": ""})()

        with patch.object(rr.subprocess, "run", side_effect=fake_run):
            changed = rr.files_changed()
        self.assertIn("new_file.py", changed)
        self.assertIn(".gitignore", changed)

    def test_files_changed_does_not_mangle_dotfiles(self):
        # Regression: `git status --porcelain`'s first line starts with a
        # 2-char status column, e.g. " M .gitignore". _run() used to .strip()
        # the whole subprocess output, which ate that line's leading space and
        # shifted files_changed()'s line[3:] slice by one character --
        # ".gitignore" silently became "gitignore". _run() must rstrip("\n")
        # only, never strip() the leading whitespace of the first line.
        changed = rr.files_changed()
        for name in changed:
            self.assertFalse(name.startswith("gitignore") and not name.startswith("."),
                              f"{name!r} looks like a mangled dotfile name")


class TestRunTestsAndEvals(unittest.TestCase):
    def test_run_eval_suite_matches_graph_evals_directly(self):
        import graph_evals as evals
        direct = evals.run_all()
        via_report = rr.run_eval_suite()
        self.assertEqual(via_report["passed"], direct.passed)
        self.assertEqual(via_report["total"], direct.total)
        self.assertEqual(via_report["all_passed"], direct.all_passed)

    def test_run_tests_shape(self):
        # A narrow, non-self-referential pattern on purpose: run_tests()'s
        # default pattern matches test_run_report.py itself, and this test
        # calling that default from inside a test run would recurse forever
        # (this test -> full discovery -> this test -> ...). test_gates.py
        # has no such self-reference, so it's safe to run for real here.
        result = rr.run_tests(pattern="test_gates.py")
        self.assertIn("run", result)
        self.assertIn("failures", result)
        self.assertIn("errors", result)
        self.assertIn("passed", result)
        self.assertGreater(result["run"], 0)
        self.assertTrue(result["passed"])

    def test_run_conformance_check_shape_and_passes_on_the_demo_dag(self):
        result = rr.run_conformance_check()
        for key in ("tasks_run", "completed", "failed", "skipped",
                    "conformance_passed", "failing_checks"):
            self.assertIn(key, result)
        self.assertTrue(result["conformance_passed"])
        self.assertEqual(result["failing_checks"], [])
        self.assertEqual(result["tasks_run"], result["completed"])
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["skipped"], 0)


class TestBuildReportAndMarkdown(unittest.TestCase):
    """
    Every call here passes test_pattern='test_gates.py' -- a real, non-empty,
    non-self-referential test run -- rather than the default full-repo
    pattern, which would match this very file and recurse without end (see
    the warning on run_report.run_tests()).
    """

    def test_build_report_defaults_next_step_from_roadmap(self):
        report = rr.build_report(test_pattern="test_gates.py")
        self.assertNotEqual(report.next_step, "")

    def test_explicit_next_step_overrides_roadmap(self):
        report = rr.build_report(next_step="Custom override", test_pattern="test_gates.py")
        self.assertEqual(report.next_step, "Custom override")

    def test_risks_default_to_empty_list(self):
        report = rr.build_report(test_pattern="test_gates.py")
        self.assertEqual(report.risks, [])

    def test_all_green_reflects_tests_and_evals(self):
        report = rr.build_report(test_pattern="test_gates.py")
        self.assertEqual(report.all_green, report.tests["passed"] and report.evals["all_passed"])

    def test_markdown_contains_every_section(self):
        report = rr.build_report(risks=["a known risk"], test_pattern="test_gates.py")
        md = report.to_markdown()
        for heading in ("Files changed", "Commands run", "Tests", "Evals",
                       "Conformance", "Risks", "Next step"):
            self.assertIn(heading, md)
        self.assertIn("a known risk", md)

    def test_markdown_reports_no_risks_noted_when_empty(self):
        report = rr.build_report(risks=[], test_pattern="test_gates.py")
        self.assertIn("none noted", report.to_markdown())


if __name__ == "__main__":
    unittest.main()
