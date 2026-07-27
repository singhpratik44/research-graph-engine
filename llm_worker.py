#!/usr/bin/env python3
"""
LLM-backed worker: the same ExtractionDirective-in / ResultEnvelope-out
contract ReferenceWorker satisfies (research_graph_workers.py), but backed by
a real model call instead of deterministic regex heuristics.

Nothing about the gate, WorkerSpawner, or the envelope contract changes: a
node this worker proposes goes through exactly the same _verify_envelope()
checks as ReferenceWorker's output. That's the point -- the governance layer
doesn't care what produced a candidate node, only whether it's schema-valid,
provenance-complete, and (if configured) entailed by its source. Swapping
ReferenceWorker for LLMWorker in graph_orchestrator.py or specialist_review.py
requires no other change anywhere in the pipeline.

`call_model` is injected (default: `_default_call_model`, a real call via the
anthropic SDK) -- the same pattern arxiv_ingest.py uses for `http_get`. This
worker's prompt-building, JSON-parsing, and envelope-construction logic is
fully testable without a network call or an API key (see test_llm_worker.py);
the real call path exists for a caller that has ANTHROPIC_API_KEY set, which
this sandbox never has, so it is written but not exercised end-to-end here --
said plainly, per CLAUDE.md rule 5, rather than left implicit.
"""

import hashlib
import json
import re
from typing import Any, Callable, Dict, List, Optional

from research_graph_schema import (
    DecisionType, ExtractionMethod, ExtractionType, Node, Provenance, Trace,
)
from research_graph_workers import ExtractionDirective, ResultEnvelope

DEFAULT_MODEL = "claude-sonnet-5"


def _slug(text: str, n: int = 6) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:n]

_REQUIRED_FIELDS: Dict[ExtractionType, List[str]] = {
    ExtractionType.CLAIMS: ["text", "subject", "relation", "object"],
    ExtractionType.CONCEPTS: ["text"],
}

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

# The JSON field contract is dictated by _REQUIRED_FIELDS, not by domain --
# every domain below shares these instructions verbatim.
_FIELD_INSTRUCTIONS: Dict[ExtractionType, str] = {
    ExtractionType.CLAIMS: (
        ' Each item must have exactly these fields: "text" (the claim, '
        'verbatim or close to it from the source), "subject" (short noun '
        'phrase), "relation" (a verb/predicate), "object" (short noun '
        'phrase), and "confidence" (a float from 0.0 to 1.0 reflecting how '
        "directly and completely the TEXT supports this exact claim -- not "
        "how plausible it sounds in general). Only include claims the TEXT "
        "actually asserts; do not paraphrase in specifics it doesn't state. "
        "Respond with ONLY the JSON array, no other text."
    ),
    ExtractionType.CONCEPTS: (
        ' Each item must have exactly these fields: "text" (the concept, '
        '1-4 words) and "confidence" (a float from 0.0 to 1.0 reflecting how '
        "central this concept is to the TEXT). Respond with ONLY the JSON "
        "array, no other text."
    ),
}


def _field_instructions(extraction_type: ExtractionType) -> Optional[str]:
    return _FIELD_INSTRUCTIONS.get(extraction_type)


# Domain-specific framing only -- what kind of source TEXT this is and what
# "claim"/"concept" means for it. Kept separate from _FIELD_INSTRUCTIONS so
# adding a domain never touches the JSON contract. "research" reproduces the
# exact original wording (the only domain this repo demonstrated before this
# feature existed), matching the three domains README.md already names this
# engine's schema/gate/query pattern generalizes to.
_DOMAIN_FRAMING: Dict[str, Dict[ExtractionType, str]] = {
    "research": {
        ExtractionType.CLAIMS:
            "Extract factual claims from the TEXT below as a JSON array.",
        ExtractionType.CONCEPTS:
            "Extract the key technical concepts from the TEXT below as a JSON array.",
    },
    "hiring": {
        ExtractionType.CLAIMS:
            "Extract factual claims about the candidate from the interview "
            "notes or reference-check TEXT below as a JSON array.",
        ExtractionType.CONCEPTS:
            "Extract the key skills, tools, and competencies the candidate "
            "TEXT below attributes to the candidate, as a JSON array.",
    },
    "ops_approval": {
        ExtractionType.CLAIMS:
            "Extract factual claims about whether the operational change or "
            "request described in the TEXT below meets its approval "
            "criteria, as a JSON array.",
        ExtractionType.CONCEPTS:
            "Extract the key operational concepts (systems, controls, risk "
            "factors) referenced in the TEXT below, as a JSON array.",
    },
    "compliance": {
        ExtractionType.CLAIMS:
            "Extract factual claims about compliance or policy adherence "
            "from the audit or review TEXT below, as a JSON array.",
        ExtractionType.CONCEPTS:
            "Extract the key compliance concepts (policies, controls, "
            "regulations) referenced in the TEXT below, as a JSON array.",
    },
}

KNOWN_DOMAINS = tuple(_DOMAIN_FRAMING.keys())


def _prompt_for(
    directive: ExtractionDirective,
    text: str,
    domain: str = "research",
    prompt_overrides: Optional[Dict[ExtractionType, str]] = None,
) -> Optional[str]:
    field_instructions = _field_instructions(directive.extraction_type)
    if field_instructions is None:
        return None

    framing = None
    if prompt_overrides is not None:
        framing = prompt_overrides.get(directive.extraction_type)
    if framing is None:
        framing = _DOMAIN_FRAMING[domain].get(directive.extraction_type)
    if framing is None:
        return None

    return f"{framing}{field_instructions}\n\nTEXT:\n{text}"


def _parse_json_array(raw: str) -> List[Dict[str, Any]]:
    """
    Defensive parse: models sometimes wrap JSON in a markdown code fence
    despite instructions not to. Strips a leading/trailing fence, then
    requires the result to be a JSON list of objects -- anything else is a
    parse failure, not silently coerced into an empty result.
    """
    stripped = _FENCE_RE.sub("", raw.strip()).strip()
    parsed = json.loads(stripped)
    if not isinstance(parsed, list):
        raise ValueError(f"expected a JSON array, got {type(parsed).__name__}")
    return parsed


def _default_call_model(model: str, prompt: str) -> str:
    """
    Real call to the Anthropic Messages API. Requires ANTHROPIC_API_KEY in
    the environment (the anthropic SDK reads it automatically). Imported
    lazily so this module loads fine without the `anthropic` package
    installed unless this exact function is actually invoked.
    """
    import anthropic

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in message.content if hasattr(block, "text"))


class LLMWorker:
    """
    Drop-in replacement for ReferenceWorker, backed by a real model instead
    of regex heuristics. Same `run(directive, text) -> ResultEnvelope`
    interface; every produced node still carries full provenance and an
    EXTRACT trace, every skip is traced with a reason, exactly like
    ReferenceWorker -- the untrusted-worker contract doesn't get relaxed
    just because the extractor got smarter.
    """

    def __init__(
        self,
        worker_id: str = "llm_worker_v1",
        model: str = DEFAULT_MODEL,
        call_model: Optional[Callable[[str, str], str]] = None,
        domain: str = "research",
        prompt_overrides: Optional[Dict[ExtractionType, str]] = None,
    ):
        if domain not in _DOMAIN_FRAMING:
            raise ValueError(
                f"unrecognized domain {domain!r}; known domains: {KNOWN_DOMAINS}")
        self.worker_id = worker_id
        self.model = model
        self.call_model = call_model or _default_call_model
        self.domain = domain
        self.prompt_overrides = prompt_overrides
        self._seq = 0

    def _trace_id(self) -> str:
        self._seq += 1
        return f"tr_{self.worker_id}_{self._seq:04d}"

    def _prov(self, directive: ExtractionDirective, conf: float) -> Provenance:
        return Provenance(directive.paper_id, ExtractionMethod.STRUCTURED_LLM.value,
                          conf, _now_placeholder(), human_reviewed=False)

    def run(self, directive: ExtractionDirective, text: str) -> ResultEnvelope:
        prompt = _prompt_for(directive, text, self.domain, self.prompt_overrides)
        if prompt is None:
            return ResultEnvelope(directive.job_id, self.worker_id, worker_status="failed",
                                  error=f"unsupported extraction_type "
                                        f"{directive.extraction_type.value}")

        try:
            raw = self.call_model(self.model, prompt)
            items = _parse_json_array(raw)
        except Exception as exc:
            return ResultEnvelope(directive.job_id, self.worker_id, worker_status="failed",
                                  error=f"model call or response parse failed: {exc!r}")

        required = _REQUIRED_FIELDS[directive.extraction_type]
        nodes: List[Node] = []
        traces: List[Trace] = []

        for item in items:
            missing = [f for f in required if not item.get(f)]
            if missing:
                traces.append(Trace(self._trace_id(), DecisionType.SKIP, self.worker_id,
                                    0.0, "MALFORMED_MODEL_OUTPUT",
                                    f"item missing required field(s) {missing}: {item!r}",
                                    input_refs=[f"{directive.paper_id}#text"]))
                continue

            conf = float(item.get("confidence", 0.0))
            if conf < directive.confidence_floor:
                traces.append(Trace(self._trace_id(), DecisionType.SKIP, self.worker_id,
                                    conf, "BELOW_DIRECTIVE_FLOOR",
                                    f"{item['text']!r} scored {conf:.2f}, under floor "
                                    f"{directive.confidence_floor:.2f}",
                                    input_refs=[f"{directive.paper_id}#text"]))
                continue

            if directive.max_results is not None and len(nodes) >= directive.max_results:
                traces.append(Trace(self._trace_id(), DecisionType.ABSTAIN, self.worker_id,
                                    conf, "MAX_RESULTS_REACHED",
                                    f"{item['text']!r} qualified but directive caps at "
                                    f"{directive.max_results}",
                                    input_refs=[f"{directive.paper_id}#text"]))
                continue

            nid = f"{directive.target_node_type.value}_{_slug(directive.paper_id + item['text'])}"
            props = {f: item[f] for f in required}
            nodes.append(Node(nid, directive.target_node_type.value, item["text"],
                              self._prov(directive, conf), props))
            traces.append(Trace(self._trace_id(), DecisionType.EXTRACT, self.worker_id,
                                conf, "MODEL_SELF_REPORTED",
                                f"model extracted {item['text']!r} with self-reported "
                                f"confidence {conf:.2f}",
                                input_refs=[f"{directive.paper_id}#text"], output_refs=[nid]))

        return ResultEnvelope(directive.job_id, self.worker_id, nodes, traces)


def _now_placeholder() -> str:
    # Deferred import to match research_graph_workers.py's own _now(); kept
    # as a tiny indirection only so tests can freeze it the same way if ever
    # needed, without importing datetime twice at module scope for no reason.
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    import os
    from research_graph_schema import ResearchGraph
    from research_graph_workers import WorkerSpawner

    text = (
        "Hierarchical orchestration reduces coordination overhead in large "
        "agent fleets. We evaluate on SWE-Bench and the PRISM benchmark."
    )
    graph = ResearchGraph()
    spawner = WorkerSpawner(graph)
    worker = LLMWorker()
    job, directive = spawner.spawn("paper_demo_llm", ExtractionType.CLAIMS)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set -- skipping the real call.")
        print("Everything above this line imports and constructs cleanly;")
        print("see test_llm_worker.py for the fully-exercised parsing/envelope logic.")
    else:
        env = worker.run(directive, text)
        result = spawner.admit(directive, env)
        print(f"admitted={result.admitted} nodes={result.nodes_admitted} "
              f"status={result.job_node.properties.get('status')}")
