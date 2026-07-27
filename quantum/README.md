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

Three dedicated literature passes informed this module, each requiring
genuine multi-paper convergence or independent verification before
counting a claim as real — direct `arxiv.org` fetch is blocked by this
sandbox's egress policy (confirmed consistent with the main repo's own
documented restriction), so arXiv coverage went through the alphaXiv
mirror and WebSearch cross-referencing instead.

1. **"Revolutionary ideas in quantum computing"** (strict 2–3-paper bar; only 3 of many candidates cleared it): independent classical dequantization overturning specific quantum-advantage claims; multi-modality/heterogeneous qubit hardware architectures; and — the one this module builds on — **LLM/agentic systems autonomously discovering new quantum error-correcting codes**, evidenced by two independent, concurrent 2026 papers (Max Planck Institute for the Science of Light; IBM), both using an LLM as the mutation operator in an open-ended structural search over qLDPC code families.
2. A follow-up set of papers on **self-optimizing quantum systems** (AutoQEC discovering its own logical subspaces and control parameters; "Useful Autonomous Quantum Machines" arguing reduced classical control is a hardware design principle; autonomous quantum-dot device bootstrapping; quantum adaptive distribution search, a hybrid loop where optimization evolves as it runs; "Quantum Agents," framing quantum-relevant tasks as an agentic sense-decide-act cycle).
3. A **user-curated, independently fact-checked list** of 10 specific papers plus a follow-up venue sweep (Quantum Journal, Nature/Nature Communications, PRX Quantum, arXiv quant-ph+cs.AI), each individually verified rather than accepted on the strength of the citation alone — several needed correction, reported honestly below rather than silently fixed.

### Verified citations (round 3)

| # | As provided | Verified reality |
|---|---|---|
| 1 | "Bounds on Autonomous Quantum Error Correction" — Quantum Journal | **Confirmed exact.** *Quantum* 9, 1804 (2025-07-22), arXiv:2308.16233. Shtanko, Liu, Lieu, Gorshkov, Albert. |
| 2 | "Autonomous error correction of a single logical qubit using a bosonic mode" — Nature Communications | **No single paper matches.** Two distinct real papers, neither matching both title and venue: (a) *"Protecting a bosonic qubit with autonomous quantum error correction"* — **Nature** 590, 243–248 (2021), arXiv:2004.09322, Gertler et al. (the bosonic-mode paper, wrong venue as claimed); (b) *"Autonomous error correction of a single logical qubit using two transmons"* — **Nature Communications** (2024-02-23), arXiv:2302.06707, Li et al. (the Nature Communications paper, but two transmons, not a bosonic mode). Listed here as two separate citations, not merged into the one the user described. |
| 3 | "Automated Discovery of Autonomous Quantum Error Correcting **Codes**" (AutoQEC) — PRX Quantum | **Confirmed, one word wrong.** Actual title ends in "**Schemes**," not "Codes": *PRX Quantum* 3, 020302 (2022), arXiv:2108.02766. Wang, Rajabzadeh, Lee, Safavi-Naeini. (A separate, newer, similarly-themed 2025 preprint, arXiv:2504.15070, does say "codes" but is not confirmed published in PRX Quantum and is not the same paper — not conflated here.) |
| 4 | "Quantum Agents" — arXiv | **Confirmed exact.** arXiv:2506.01536 (2025-06-02). Sultanow, Tehrani, Dutta, Buchanan, Khan. |
| 5 | Open-source framework for quantum hardware control — arXiv | **Confirmed exact**, referring to Qibolab. *"An open-source framework for quantum hardware control"*, arXiv:2407.21737 (2024-07-31). Pedicillo et al. |
| 6 | "Autonomous bootstrapping of quantum dot devices" — arXiv | **Confirmed exact**, arXiv:2407.20061 (2024-07-29), also formally published in *Physical Review Applied* 23, 014072 (2025). Zubchenko, Middlebrooks, Rasmussen, Lausen, Kuemmeth, Chatterjee, Zwolak. |
| 7 | "Beating the break-even point with autonomous quantum error correction" — arXiv | **Confirmed exact.** arXiv:2504.16746 (2025-04-23). Li, Mei, Jie, Cai, et al. |
| 8 | "SAQ: Stabilizer-Aware Quantum Error Correction Decoder" — OpenReview | **Confirmed exact**, an ICLR 2026 submission (forum `ySp8faVj6k`), arXiv:2512.08914. **Accept/reject decision unverified** — direct OpenReview fetch 403'd; not claimed here as accepted. |
| 9 | "Automating quantum feature map design via large language models" — arXiv | **Confirmed exact.** arXiv:2504.07396 (2025-04). Sakka, Mitarai, Fujii (Osaka University / RIKEN). |
| 10 | "What is my quantum computer good for?" — NeurIPS | **Confirmed, title truncated.** Full title: *"What is my quantum computer good for? Quantum capability learning with physics-aware neural networks"* — NeurIPS 2024, arXiv:2406.05636. |

**New, genuinely in-window (late April–July 2026) finds from the follow-up venue sweep** — none of these were in the original 10, each independently confirmed real: *"Vibe Calibration: Autonomous Bring-up of a 112-Qubit Superconducting Quantum Processor by a Skill-Orchestrating Language Agent"* (arXiv:2606.22376, 2026-06-21) — an LLM agent autonomously bringing up real hardware, the closest thing found in this entire research effort to an actual "agentic quantum system" running on physical qubits; *"An LLM System for Autonomous Variational Quantum Circuit Design"* (arXiv:2606.13380, 2026-06-11), a direct follow-up to #9 by the same lead author; *"LLM-Driven Cross-Paradigm Design for Quantum Optimal Control"* (arXiv:2607.17498, 2026-07-20). Quantum Journal, Nature Communications, and PRX Quantum themselves yielded nothing new and on-topic in this specific window — reported honestly rather than padded.

`autonomous_loop.py` is the concrete synthesis of item 2 above (and now
reinforced by items 3/4, 6/7, and the Vibe Calibration find), run over the
real code machinery from item 1 and `css_codes.py`/`hypergraph_product.py`
— not a reimplementation of any single paper's actual algorithm (no real
quantum hardware or learned optimizer is involved), but a genuine instance
of the control-loop *structure* those papers converge on.

**Explicitly out of scope**, said plainly rather than glossed over: the
"quantum learning advantage on a scalable photonic platform" paper from
the first research pass, and every hardware-bring-up/control-electronics
paper in the table below (Gertler et al.'s bosonic qubit, Li et al.'s
two-transmon logical qubit, Zubchenko et al.'s quantum-dot bootstrapping,
Vibe Calibration's 112-qubit bring-up) are real experiments on real
hardware — there is no classical-simulation equivalent to build for any
of them, so none are reflected in this module beyond being named in the
research record above.

### Quantum stack layers and governance levers

A layered view of the full quantum computing stack these papers span,
each layer's representative sources, and the governance levers a
production deployment would need at that layer — contributed as a
reference framework, annotated here against what this module actually
implements (most layers below are hardware or application-integration
concerns with no classical-simulation equivalent; **only layer 3, and
part of layer 5, are implemented in this repo**):

| Layer | Representative sources | What it does | Implemented here? |
|---|---|---|---|
| 0. Physical qubits & control electronics | Gertler et al., *Nature* 2021; Li et al., *Nature Communications* 2024; "Beating the break-even point" arXiv:2504.16746 | Raw qubit modalities and RF/microwave/laser control electronics everything else depends on. | **No** — real hardware, out of scope for a classical-simulation module. |
| 1. Open control frameworks & telemetry | "An open-source framework for quantum hardware control" (Qibolab), arXiv:2407.21737 | Programmable APIs for pulses, schedules, calibration, readout, plus telemetry. | **No** — would require real hardware/driver integration. |
| 2. ML-assisted quantum control | (pulse-shape/control-policy learning literature, not individually verified in this pass) | ML models finding high-fidelity pulse shapes or control policies under uncertainty. | **No** — pulse-level control is a different problem than code-level QEC design. |
| 3. Autonomous quantum error correction (AQEC) | "Bounds on Autonomous QEC," *Quantum* 2025; "Automated Discovery of Autonomous QEC Schemes," *PRX Quantum* 2022; Gertler/Li hardware AQEC papers | Engineered dissipation/feedback maintaining logical qubits with minimal classical intervention. | **Yes** — `css_codes.py`, `hypergraph_product.py`, `qec_simulation.py` are real stabilizer-code/QEC machinery; distance and logical-error-rate are computed, not asserted. |
| 4. Autonomous bootstrapping & self-configuration | "Autonomous bootstrapping of quantum dot devices," arXiv:2407.20061; "Vibe Calibration," arXiv:2606.22376 | Automatic device initialization/tuning from a cold start into a known-good regime. | **Partially, in spirit** — `autonomous_loop.py` self-initializes from a starting code and self-tunes toward a better one without a human picking the next candidate; it is a software analog, not literal hardware bring-up. |
| 5. Quantum-aware agentic orchestration | "Quantum Agents," arXiv:2506.01536; "Automating quantum feature map design via LLMs," arXiv:2504.07396; "SAQ" decoder, OpenReview; "An LLM System for Autonomous Variational Quantum Circuit Design," arXiv:2606.13380 | Agents planning/scheduling/optimizing calibration, circuit design, or decoder selection. | **Yes, in spirit** — `code_search.py`'s injectable mutation hook and `autonomous_loop.py`'s sense-decide-optimize-verify-reconfigure cycle are the software analog; the default mutation operator is a simple random perturbation, not a real LLM (see Honesty notes). |
| 6. Physics-aware capability modeling | "What is my quantum computer good for?", NeurIPS 2024 | Realistic per-device capability models (noise, depth, connectivity) guiding routing/scheduling decisions. | **No** — a genuine, buildable next step (model a specific code's error profile as a "capability report"), not built in this round. |
| 7. Domain applications (enterprise & defense) | (not independently verified in this pass) | Integrating quantum subsystems into drug discovery, logistics, secure comms, sensing. | **No** — application-layer integration, out of scope for this module. |

The "governance levers" column from the original framework (hardware
qualification requirements, control-API audit logging, ML-controller
verification/rollback, AQEC error-budget certification, bootstrapping
change-management, agent tool/action allowlisting, capability-model
uncertainty quantification, domain risk assessments) is a real and
coherent idea for a *deployed* quantum stack, but is not something a
classical-simulation research module can meaningfully implement — noted
here for completeness, not built.

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
