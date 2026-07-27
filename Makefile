.PHONY: test inspect roadmap evals conformance validate web report typecheck

test:
	python3 -m unittest discover -p "test_*.py"

# Static type check (mypy.ini). Separate from `validate` on purpose -- CLAUDE.md's
# definition of "done" is test + evals + conformance; this is additional rigor,
# not a redefinition of that contract. Needs requirements-dev.txt installed.
typecheck:
	python3 -m mypy $(wildcard *.py)

inspect:
	python3 graph_inspector.py

roadmap:
	python3 graph_roadmap.py

evals:
	python3 graph_evals.py

# Validates a whole task-DAG run: every task has exactly one span, span
# status matches the task's final status, timing isn't backwards,
# completed/failed/skipped exactly partition the DAG, no dependency cycles,
# every completed span recorded a confidence. Exits non-zero on any failure.
conformance:
	python3 task_conformance.py

# The one thing an autonomous run must pass before it's done: tests + evals,
# together, in one deterministic command. See CLAUDE.md.
validate: test evals conformance

web:
	uvicorn webapp:app --reload

report:
	python3 run_report.py
