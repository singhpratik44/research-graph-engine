#!/usr/bin/env python3
"""
Phase 11: Structured run reporting

Per ROADMAP.md's workflow rules: every autonomous run ends with a structured
report -- files changed, commands run, tests passing, risks, next step --
not a prose claim that things worked. Mechanical parts (branch, diff, test
counts, eval counts) are computed for real via git and the actual test/eval
runners; only `risks` and `next_step` take human/agent judgment as input,
and next_step defaults to whatever ROADMAP.md's "## Next" section says so it
can't silently drift from the roadmap.

Writes run_report.json and prints the same report as markdown.
"""

import argparse
import io
import json
import subprocess
import unittest
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import graph_evals as evals

REPO_ROOT = Path(__file__).resolve().parent
ROADMAP_PATH = REPO_ROOT / "ROADMAP.md"
REPORT_PATH = REPO_ROOT / "run_report.json"


def _run(cmd: List[str]) -> str:
    # rstrip only: `git status --porcelain` uses a fixed 2-char status column
    # on every line, including the first -- a plain .strip() eats that line's
    # leading space and corrupts files_changed()'s line[3:] slice (".gitignore"
    # silently becomes "gitignore"). Only ever trim the trailing newline.
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    return result.stdout.rstrip("\n")


def current_branch() -> str:
    return _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"


def _merge_base() -> Optional[str]:
    for ref in ("origin/main", "main"):
        base = _run(["git", "merge-base", "HEAD", ref])
        if base:
            return base
    return None


def files_changed(base: Optional[str] = None) -> List[str]:
    """
    Files touched relative to `base` (default: merge-base with origin/main or
    main, whichever resolves), plus anything currently uncommitted. Read-only:
    runs `git diff`/`git status`, never mutates the working tree.
    """
    base = base if base is not None else _merge_base()
    changed = set()
    if base:
        diff = _run(["git", "diff", "--name-only", f"{base}...HEAD"])
        changed.update(f for f in diff.splitlines() if f)
    for line in _run(["git", "status", "--porcelain"]).splitlines():
        if line:
            changed.add(line[3:].strip())
    return sorted(changed)


def run_tests(pattern: str = "test_*.py") -> Dict:
    """
    Runs the suite matching `pattern` via unittest discovery. NOTE: this file's
    own tests (test_run_report.py) must never call run_tests() with the
    default full-repo pattern -- that pattern matches test_run_report.py
    itself, and a test that re-triggers full discovery from inside a test run
    recurses without end. Tests exercise this with a narrower pattern instead.
    """
    suite = unittest.TestLoader().discover(str(REPO_ROOT), pattern=pattern)
    result = unittest.TextTestRunner(verbosity=0, stream=io.StringIO()).run(suite)
    return {
        "run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "passed": result.wasSuccessful(),
    }


def run_eval_suite() -> Dict:
    report = evals.run_all()
    return {
        "passed": report.passed,
        "total": report.total,
        "all_passed": report.all_passed,
        "failing": [r.name for r in report.failures()],
    }


def next_roadmap_step() -> str:
    """
    First unchecked '- [ ]' item under '## Next' in ROADMAP.md, including any
    indented continuation lines that wrap the same bullet, up to the next
    bullet/heading/blank line.
    """
    if not ROADMAP_PATH.exists():
        return "(no ROADMAP.md found)"
    lines = ROADMAP_PATH.read_text().splitlines()
    in_next = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## "):
            in_next = stripped.lower() == "## next"
            continue
        if in_next and stripped.startswith("- [ ]"):
            parts = [stripped[len("- [ ]"):].strip()]
            for cont in lines[i + 1:]:
                cont_stripped = cont.strip()
                if not cont_stripped or cont_stripped.startswith(("- [", "## ")):
                    break
                parts.append(cont_stripped)
            return " ".join(parts)
    return "(no pending item found under '## Next')"


@dataclass
class RunReport:
    timestamp: str
    branch: str
    files_changed: List[str]
    commands_run: List[str]
    tests: Dict
    evals: Dict
    risks: List[str] = field(default_factory=list)
    next_step: str = ""

    @property
    def all_green(self) -> bool:
        return self.tests["passed"] and self.evals["all_passed"]

    def to_markdown(self) -> str:
        lines = [
            f"# Run report ({self.timestamp})",
            f"- branch: `{self.branch}`",
            f"- overall: {'GREEN' if self.all_green else 'RED'}",
            "",
            f"## Files changed ({len(self.files_changed)})",
        ]
        lines += [f"- `{f}`" for f in self.files_changed] or ["(none)"]
        lines += [
            "",
            "## Commands run",
        ]
        lines += [f"- `{c}`" for c in self.commands_run]
        lines += [
            "",
            "## Tests",
            f"- {self.tests['run']} run, {self.tests['failures']} failed, "
            f"{self.tests['errors']} errors -- "
            f"{'PASS' if self.tests['passed'] else 'FAIL'}",
            "",
            "## Evals",
            f"- {self.evals['passed']}/{self.evals['total']} passed",
        ]
        if self.evals["failing"]:
            lines.append(f"- failing: {', '.join(self.evals['failing'])}")
        lines += [
            "",
            "## Risks",
        ]
        lines += [f"- {r}" for r in self.risks] or ["- none noted"]
        lines += [
            "",
            "## Next step",
            self.next_step,
        ]
        return "\n".join(lines)


def build_report(
    risks: Optional[List[str]] = None,
    next_step: Optional[str] = None,
    base: Optional[str] = None,
    test_pattern: str = "test_*.py",
) -> RunReport:
    """
    test_pattern exists so this file's own tests can pass something narrower
    than the default -- see the warning on run_tests(). Real callers (the CLI
    below, `make report`) always want the default full-repo pattern.
    """
    return RunReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        branch=current_branch(),
        files_changed=files_changed(base),
        commands_run=["git diff/status", f"unittest discover -p {test_pattern}", "graph_evals.run_all()"],
        tests=run_tests(test_pattern),
        evals=run_eval_suite(),
        risks=risks or [],
        next_step=next_step or next_roadmap_step(),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--risk", action="append", default=[],
                         help="A known risk to record for this run (repeatable).")
    parser.add_argument("--next", dest="next_step", default=None,
                         help="Override the auto-detected next step (default: ROADMAP.md's '## Next').")
    parser.add_argument("--base", default=None,
                         help="Git ref to diff against (default: merge-base with origin/main or main).")
    args = parser.parse_args()

    report = build_report(risks=args.risk, next_step=args.next_step, base=args.base)
    REPORT_PATH.write_text(json.dumps(asdict(report), indent=2) + "\n")
    print(report.to_markdown())
    print(f"\n(written to {REPORT_PATH.relative_to(REPO_ROOT)})")


if __name__ == "__main__":
    main()
