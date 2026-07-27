# quantum/

A **separate, standalone implementation** inside this repository — not
integrated with the research-graph-engine (the governed knowledge-graph
system the rest of this repo implements). It shares no code, no schema,
and no governance pattern with the main engine; it exists here because the
main engine's own literature corpus already treats quantum computing
research as example domain data, and this module is a real, from-scratch
answer to "what would an actual quantum-computing implementation look
like," built from a dedicated literature research pass rather than a
toy demo.

## What this is

Real stabilizer/CSS quantum error-correcting code machinery — genuine
GF(2) linear algebra, not a simulation of a simulation — plus an
autonomous, self-optimizing control loop built on top of it. Every
numeric claim below is independently checkable against standard quantum
error correction references (e.g. the Steane code's `[[7, 1, 3]]`
parameters), not just internally self-consistent.

| Module | What it does |
|---|---|
| `gf2.py` | GF(2) (binary) linear algebra: rank, row reduction, nullspace/kernel, Kronecker product, and linear system solving — the pure-math foundation everything else sits on. |
| `css_codes.py` | `CSSCode`/`build_css_code()` — construct a real CSS stabilizer code from two classical parity-check matrices `H_X`/`H_Z`, computing the standard `[[n, k, d]]` parameters: physical qubits, logical qubits, symplectically-paired logical X/Z operators, and (via `compute_distance()`, bounded brute force) the code distance. |
| `hypergraph_product.py` | The Tillich–Zémor hypergraph product: turns a single classical parity-check matrix into a real quantum LDPC code family — the same construction family (lifted-product / bivariate-bicycle codes) that two independent 2026 research groups (Max Planck Institute for the Science of Light; IBM) used LLM-guided structured search to discover new instances of. |
| `qec_simulation.py` | Monte Carlo logical error rate estimation: exact coset-leader syndrome-table decoding, independent X/Z error channels, reproducible via an injectable `random.Random`. |
| `code_search.py` | Pure search primitives — a bounded mutation operator over classical base codes and a `[[n,k,d]]`-based scoring heuristic — with an injectable mutation hook (the same pattern the main engine's `llm_worker.py` uses for its injectable `call_model`) so a real LLM-guided proposer could be swapped in without touching anything else. |
| `autonomous_loop.py` | The actual self-optimizing system: a **sense → decide → optimize → verify → reconfigure** loop that autonomously searches for, verifies (via real Monte Carlo simulation, not just trusting the search score), and adopts better-performing codes over successive rounds, stopping itself once improvement stalls. |

## Research provenance

Two dedicated literature passes (arXiv via the alphaXiv mirror — direct
`arxiv.org` fetch is blocked by this sandbox's egress policy, confirmed
consistent with the main repo's own documented restriction) informed this
module, both requiring genuine 2–3-paper convergence before counting an
idea as real:

1. **"Revolutionary ideas in quantum computing"** (strict bar; only 3 of many candidates cleared it): independent classical dequantization overturning specific quantum-advantage claims; multi-modality/heterogeneous qubit hardware architectures; and — the one this module actually builds on — **LLM/agentic systems autonomously discovering new quantum error-correcting codes**, evidenced by two independent, concurrent 2026 papers (Max Planck Institute for the Science of Light; IBM), both using an LLM as the mutation operator in an open-ended structural search over qLDPC code families.
2. A follow-up set of papers on **self-optimizing quantum systems** (AutoQEC discovering its own logical subspaces and control parameters; "Useful Autonomous Quantum Machines" arguing reduced classical control is a hardware design principle; autonomous quantum-dot device bootstrapping; quantum adaptive distribution search, a hybrid loop where optimization evolves as it runs; "Quantum Agents," framing quantum-relevant tasks as an agentic sense-decide-act cycle).

`autonomous_loop.py` is the concrete synthesis of (2), run over the real
code machinery from (1) and `css_codes.py`/`hypergraph_product.py` — not a
reimplementation of any single paper's actual algorithm (no real quantum
hardware or learned optimizer is involved), but a genuine instance of the
control-loop *structure* those papers converge on.

**Explicitly out of scope**, said plainly rather than glossed over: the
"quantum learning advantage on a scalable photonic platform" paper from
the same research pass is a real hardware experiment — there is no
classical-simulation equivalent to build here, so it isn't reflected in
this module beyond being named in the research record above.

## Quickstart

```bash
cd quantum

# run every test in this module (93 tests, ~13s -- some brute-force
# distance/decoding searches are genuinely exponential in qubit count,
# by construction; see css_codes.compute_distance's docstring)
python3 -m unittest discover -p "test_*.py"

# static type check
python3 -m mypy --ignore-missing-imports *.py

# see the autonomous loop actually run, starting from a length-3
# repetition code
python3 autonomous_loop.py
```

```python
import css_codes

# The Steane [[7, 1, 3]] code, independently checkable against any
# quantum error correction reference
HAMMING_7_4_3 = [
    [1, 0, 1, 0, 1, 0, 1],
    [0, 1, 1, 0, 0, 1, 1],
    [0, 0, 0, 1, 1, 1, 1],
]
code = css_codes.build_css_code(HAMMING_7_4_3, HAMMING_7_4_3)
print(code.n, code.k)                        # 7 1
print(css_codes.compute_distance(code))      # 3
```

## Honesty notes

- Distance computation and syndrome-table construction are **brute force**
  and exponential in qubit count by construction — there is no known
  efficient exact algorithm for general stabilizer-code minimum distance.
  Both default to a small qubit-count ceiling (documented in each
  function's docstring) rather than silently running forever on a code
  too large for this approach.
- `code_search.py`'s default mutation operator is a **deliberately simple
  random perturbation**, not the LLM-guided search the cited research
  papers actually use — that gap is stated plainly in the module
  docstring, mirroring the same "this heuristic proves the loop closes,
  it is not the sophisticated thing itself" posture the main engine's
  `ReferenceWorker` takes for its own, different reason.
- `code_search.score_code()`'s `k * d / n` scoring heuristic is one
  simple, explicit choice for comparing candidates — not a claim that it's
  the objective real qLDPC code search should optimize.
