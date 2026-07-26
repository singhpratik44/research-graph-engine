# Working in this repo (Claude Code / any autonomous agent)

This repo is deliberately structured for machine-readable, deterministic
autonomous work: closed enums instead of freeform strings, structured traces
instead of prose, one command per validation step. Follow that shape when
adding to it — don't reintroduce ambiguity the rest of the codebase spent
effort removing.

## Rules

1. **One bounded item per run.** Work the single item under `## Next` in
   `ROADMAP.md`. Do not also start the next backlog item in the same run,
   even if it looks quick — a run that touches two roadmap items produces a
   report neither item's history can be cleanly attributed to.
2. **Work only on a branch.** Never commit or push directly to `main`.
3. **Read before you extend.** `research_graph_schema.py`'s `NODE_SCHEMA`
   and `research_graph_gates.py`'s six checks are the contract every other
   module assumes holds. If a change touches either, re-run
   `python3 -m unittest test_schema.py test_gates.py test_workers.py`
   specifically, not just the full suite, and read the failure if anything
   moves.
4. **Read-only modules stay read-only.** `graph_inspector.py`,
   `graph_queries.py`, `graph_roadmap.py`, and `webapp.py` never mutate a
   graph — that contract is asserted in each module's own docstring and
   leaned on by the others (`graph_inspector` calls into `graph_queries`,
   `webapp` calls into all three). If a task seems to need one of them to
   write, that's a sign the write belongs in `research_graph_workers.py`
   instead, not a reason to add a mutating method to a read-only module.
5. **Full relevant validation before calling anything done:**
   - Always: `make test` (or `make validate`, which is `test` + `evals`).
   - Schema/gate/worker changes: also `make inspect` and `make roadmap` —
     confirm the golden fixtures and the literature corpus still render
     sanely, not just that assertions pass.
   - UI changes: start `uvicorn webapp:app` and hit the changed route for
     real (`curl`, or a Playwright screenshot) — a 200 from `TestClient` is
     necessary, not sufficient.
   - New external calls: expect this sandbox's egress policy to block
     unlisted hosts (confirmed for `arxiv.org`, `huggingface.co`,
     `blog.langchain.com` — a 403 at the proxy tunnel, before any HTTP
     request lands). Do not retry or route around a blocked host. Write the
     real call, test it against an injected/mocked transport, and say
     plainly in the run report that live verification is blocked.
6. **Every run ends with a structured report, not a prose claim.** Run
   `python3 run_report.py` (or `make report`) before saying a task is done.
   It computes files changed, test/eval counts, and the next roadmap step
   for real from git and the actual test/eval runners — only `--risk` is
   free-text judgment, and even that goes in the same structured artifact
   rather than a paragraph a human has to parse.
7. **Never make `run_report.py`'s own tests call its default test pattern.**
   `run_tests()`'s default pattern (`test_*.py`) matches `test_run_report.py`
   itself; a test in that file calling `run_tests()` with the default
   pattern re-triggers full discovery from inside a test run and recurses
   without end. This already happened once — `test_run_report.py`'s tests
   pass `test_pattern="test_gates.py"` specifically to stay non-self-
   referential. Keep it that way if you touch that file.
8. **Stop and ask, don't guess, when:**
   - A schema/gate change would change what an *existing* golden fixture or
     literature-corpus node validates to (a broken test here means the
     contract moved, not that the test is wrong).
   - A task implies a mutating web endpoint (approve/waive from the UI).
     That's a deliberate scope boundary (see rule 4), not an oversight —
     confirm before crossing it.
   - Git history looks like someone else's in-progress work (unfamiliar
     branches, uncommitted changes you didn't make). Stash or move aside,
     never discard.
9. **A human reviews and merges.** Moving the completed item from `## Next`
   to `## Done` in `ROADMAP.md` and promoting the next backlog item happens
   at merge time, not preemptively on the same branch.

## Quick reference

See `README.md` for the file-to-layer map and `ROADMAP.md` for what's next.
`make test`, `make inspect`, `make roadmap`, `make evals`, `make validate`,
`make web`, `make report` cover every entry point this repo currently has.
