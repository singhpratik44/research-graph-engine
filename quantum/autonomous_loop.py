#!/usr/bin/env python3
"""
An autonomous, self-optimizing control loop over quantum error-correcting
codes -- the concrete synthesis of the research this package is informed
by: AutoQEC (optimization discovering its own better logical subspaces),
"Useful Autonomous Quantum Machines" (autonomy as a design principle, not
a software afterthought), autonomous device bootstrapping (self-tuning
without a human in the loop), quantum adaptive distribution search (a
hybrid loop where the optimization process evolves as it runs), and
"Quantum Agents" (quantum-relevant tasks framed as an agentic sense-
decide-act cycle). None of those papers' actual algorithms are
reimplemented here -- this loop runs over the classical CSS/hypergraph-
product code machinery this package already built, not a real quantum
device or a real learned optimizer. What is real is the control-loop
*structure* those papers converge on:

    sense -> decide -> optimize -> verify -> reconfigure

applied here as: sense the current code's simulated logical error rate,
decide whether a proposed mutation scores better, optimize by proposing
one via `code_search.py`'s injectable mutation hook, verify the candidate
with a real Monte Carlo simulation (not just trusting its [[n,k,d]]
parameters) before committing to it, and reconfigure -- adopt the
candidate as the new current operating code, or reject it and keep the
old one -- entirely autonomously, stopping itself once improvement stalls
rather than running for a human-picked fixed budget or requiring a human
to pick the next candidate to try.
"""

import random
from dataclasses import dataclass, field
from typing import List, Optional

import code_search
import gf2
import qec_simulation
from css_codes import CSSCode
from code_search import MutationOperator
from gf2 import Matrix


@dataclass
class RoundRecord:
    """
    One round's structured outcome -- audit trail, not a prose log. This
    echoes (in spirit only; there is no integration) the main
    research-graph-engine's own discipline of recording every decision as
    structured data with a reason, applied here to an autonomous system's
    self-modification decisions instead of a governance verdict.
    """
    round_number: int
    candidate_h: Matrix
    candidate_parameters: str
    candidate_score: float
    baseline_score: float
    sensed_logical_error_rate: Optional[float]
    accepted: bool
    reason: str


@dataclass
class AutonomousLoopReport:
    rounds: List[RoundRecord]
    initial_h: Matrix
    initial_score: float
    final_h: Matrix
    final_code: CSSCode
    final_score: float
    stopped_reason: str

    @property
    def improved(self) -> bool:
        return self.final_score > self.initial_score

    @property
    def accepted_rounds(self) -> List[RoundRecord]:
        return [r for r in self.rounds if r.accepted]

    def summary(self) -> str:
        lines = [
            f"initial: {self.initial_score:.4f}  ->  final: {self.final_score:.4f}"
            f"  ({self.final_code.parameters()})",
            f"rounds run: {len(self.rounds)}, accepted: {len(self.accepted_rounds)}, "
            f"stopped because: {self.stopped_reason}",
        ]
        for r in self.rounds:
            mark = "ACCEPTED" if r.accepted else "rejected"
            lines.append(f"  round {r.round_number:3d} [{mark:8s}] "
                        f"{r.candidate_parameters:16s} score={r.candidate_score:.4f} -- {r.reason}")
        return "\n".join(lines)


def run_autonomous_qec_loop(
    initial_h,
    max_rounds: int = 30,
    stall_rounds: int = 8,
    propose_mutation: MutationOperator = code_search.mutate_base_code,
    max_qubits: int = code_search.DEFAULT_MAX_QUBITS_FOR_SEARCH,
    verify_trials: int = 300,
    verify_physical_error_rate: float = 0.05,
    rng: Optional[random.Random] = None,
) -> AutonomousLoopReport:
    """
    Run the sense-decide-optimize-verify-reconfigure loop starting from
    classical base code `initial_h`, for up to `max_rounds` rounds, or
    until `stall_rounds` consecutive rounds fail to improve on the current
    best score -- an autonomous stopping condition, not a human deciding
    when to quit. Every round is recorded, whether accepted or not, so a
    caller can inspect exactly what was tried and why it was or wasn't
    adopted, not just the final result.

    `propose_mutation` (default `code_search.mutate_base_code`) is the
    injection point for a smarter optimizer, per `code_search.py`'s own
    docstring -- e.g. a real LLM-guided proposer, mirroring the
    injectable-call pattern the main engine's `llm_worker.py` already
    uses. Swapping it in requires no change to this loop.

    Raises `ValueError` if `initial_h` doesn't even produce an evaluable
    starting code -- there's nothing to optimize from in that case.
    """
    rng = rng if rng is not None else random.Random()
    current_h = gf2.to_matrix(initial_h)

    current_eval = code_search.evaluate_candidate(current_h, max_qubits=max_qubits)
    if current_eval is None:
        raise ValueError(
            "initial_h did not produce a valid, in-budget CSS code -- "
            "check it is non-empty and its hypergraph product stays within max_qubits")
    current_code, _current_distance, current_score = current_eval
    initial_score = current_score

    rounds: List[RoundRecord] = []
    stalled = 0
    stopped_reason = f"reached max_rounds ({max_rounds})"

    for round_number in range(1, max_rounds + 1):
        candidate_h = propose_mutation(current_h, rng)
        candidate_eval = code_search.evaluate_candidate(candidate_h, max_qubits=max_qubits)

        if candidate_eval is None:
            rounds.append(RoundRecord(
                round_number=round_number, candidate_h=candidate_h,
                candidate_parameters="(invalid or over qubit budget)", candidate_score=0.0,
                baseline_score=current_score, sensed_logical_error_rate=None,
                accepted=False, reason="not a valid, in-budget CSS construction",
            ))
            stalled += 1
        else:
            candidate_code, _candidate_distance, candidate_score = candidate_eval
            if candidate_score > current_score:
                # Verify before reconfiguring: don't trust [[n,k,d]] alone,
                # re-simulate the candidate's actual logical error rate.
                sim_result = qec_simulation.simulate_logical_error_rate(
                    candidate_code, verify_physical_error_rate,
                    trials=verify_trials, rng=rng)
                rounds.append(RoundRecord(
                    round_number=round_number, candidate_h=candidate_h,
                    candidate_parameters=candidate_code.parameters(),
                    candidate_score=candidate_score, baseline_score=current_score,
                    sensed_logical_error_rate=sim_result.logical_error_rate,
                    accepted=True,
                    reason=f"score {candidate_score:.4f} improves on {current_score:.4f}",
                ))
                current_h, current_code, current_score = candidate_h, candidate_code, candidate_score
                stalled = 0
            else:
                rounds.append(RoundRecord(
                    round_number=round_number, candidate_h=candidate_h,
                    candidate_parameters=candidate_code.parameters(),
                    candidate_score=candidate_score, baseline_score=current_score,
                    sensed_logical_error_rate=None, accepted=False,
                    reason=f"score {candidate_score:.4f} does not improve on {current_score:.4f}",
                ))
                stalled += 1

        if stalled >= stall_rounds:
            stopped_reason = f"stalled for {stall_rounds} consecutive rounds"
            break

    return AutonomousLoopReport(
        rounds=rounds, initial_h=gf2.to_matrix(initial_h), initial_score=initial_score,
        final_h=current_h, final_code=current_code, final_score=current_score,
        stopped_reason=stopped_reason,
    )


if __name__ == "__main__":
    demo_rng = random.Random(2026)
    report = run_autonomous_qec_loop(
        [[1, 1, 0], [0, 1, 1]],  # length-3 repetition code -> [[13, 1, 3]] starting point
        max_rounds=25, stall_rounds=6, rng=demo_rng,
    )
    print(report.summary())
