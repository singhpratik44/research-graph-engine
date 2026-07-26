.PHONY: test inspect roadmap evals validate web report

test:
	python3 -m unittest discover -p "test_*.py"

inspect:
	python3 graph_inspector.py

roadmap:
	python3 graph_roadmap.py

evals:
	python3 graph_evals.py

# The one thing an autonomous run must pass before it's done: tests + evals,
# together, in one deterministic command. See CLAUDE.md.
validate: test evals

web:
	uvicorn webapp:app --reload

report:
	python3 run_report.py
