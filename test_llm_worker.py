#!/usr/bin/env python3
"""
Test suite for llm_worker.py. `call_model` is always injected here -- no
network call, no API key -- proving the prompt-building, JSON-parsing, and
envelope-construction logic independent of any real model, the same way
test_arxiv_ingest.py proves arxiv_ingest.py's parsing against an injected
`http_get` instead of a live HTTP call.
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from research_graph_schema import ExtractionType, ResearchGraph
from research_graph_workers import WorkerSpawner
import llm_worker as lw

PAPER = "paper_demo_llm"
TEXT = "Hierarchical orchestration reduces coordination overhead."


def _spawn(extraction_type=ExtractionType.CLAIMS, **kw):
    graph = ResearchGraph()
    spawner = WorkerSpawner(graph)
    job, directive = spawner.spawn(PAPER, extraction_type, **kw)
    return spawner, graph, directive


class TestPromptFor(unittest.TestCase):
    def test_claims_prompt_mentions_required_fields(self):
        _, _, directive = _spawn(ExtractionType.CLAIMS)
        prompt = lw._prompt_for(directive, TEXT)
        for field in ("subject", "relation", "object", "confidence"):
            self.assertIn(field, prompt)
        self.assertIn(TEXT, prompt)

    def test_concepts_prompt_mentions_required_fields(self):
        _, _, directive = _spawn(ExtractionType.CONCEPTS)
        prompt = lw._prompt_for(directive, TEXT)
        self.assertIn("confidence", prompt)
        self.assertIn(TEXT, prompt)

    def test_unsupported_extraction_type_returns_none(self):
        _, _, directive = _spawn(ExtractionType.METHODS)
        self.assertIsNone(lw._prompt_for(directive, TEXT))


class TestParseJsonArray(unittest.TestCase):
    def test_parses_plain_json_array(self):
        out = lw._parse_json_array('[{"text": "a"}]')
        self.assertEqual(out, [{"text": "a"}])

    def test_strips_markdown_code_fence(self):
        raw = '```json\n[{"text": "a"}]\n```'
        self.assertEqual(lw._parse_json_array(raw), [{"text": "a"}])

    def test_strips_bare_fence_without_language_tag(self):
        raw = '```\n[{"text": "a"}]\n```'
        self.assertEqual(lw._parse_json_array(raw), [{"text": "a"}])

    def test_non_list_json_raises(self):
        with self.assertRaises(ValueError):
            lw._parse_json_array('{"text": "a"}')

    def test_malformed_json_raises(self):
        with self.assertRaises(json.JSONDecodeError):
            lw._parse_json_array("not json at all")


class TestLLMWorkerRun(unittest.TestCase):
    def test_happy_path_produces_traced_claim_nodes(self):
        items = [
            {"text": "Hierarchical orchestration reduces coordination overhead.",
             "subject": "hierarchical orchestration", "relation": "reduces",
             "object": "coordination overhead", "confidence": 0.87},
        ]
        worker = lw.LLMWorker(call_model=lambda model, prompt: json.dumps(items))
        _, _, directive = _spawn(ExtractionType.CLAIMS)
        env = worker.run(directive, TEXT)

        self.assertEqual(env.worker_status, "completed")
        self.assertEqual(len(env.nodes), 1)
        node = env.nodes[0]
        self.assertEqual(node.type, "claim")
        self.assertEqual(node.properties["subject"], "hierarchical orchestration")
        self.assertAlmostEqual(node.provenance.confidence, 0.87)
        self.assertEqual(node.provenance.source_paper, PAPER)
        self.assertFalse(node.provenance.human_reviewed)

        extract_traces = [t for t in env.traces if t.decision_type.value == "extract"]
        self.assertEqual(len(extract_traces), 1)
        self.assertEqual(extract_traces[0].output_refs, [node.id])

    def test_concepts_extraction_produces_concept_nodes(self):
        items = [{"text": "orchestration", "confidence": 0.7}]
        worker = lw.LLMWorker(call_model=lambda model, prompt: json.dumps(items))
        _, _, directive = _spawn(ExtractionType.CONCEPTS)
        env = worker.run(directive, TEXT)
        self.assertEqual(env.nodes[0].type, "concept")
        self.assertEqual(env.nodes[0].properties, {"text": "orchestration"})

    def test_item_missing_required_field_is_skipped_not_dropped_silently(self):
        items = [{"text": "incomplete claim", "confidence": 0.9}]  # no subject/relation/object
        worker = lw.LLMWorker(call_model=lambda model, prompt: json.dumps(items))
        _, _, directive = _spawn(ExtractionType.CLAIMS)
        env = worker.run(directive, TEXT)
        self.assertEqual(env.nodes, [])
        skip_traces = [t for t in env.traces if t.decision_type.value == "skip"]
        self.assertEqual(len(skip_traces), 1)
        self.assertEqual(skip_traces[0].reason_code, "MALFORMED_MODEL_OUTPUT")

    def test_confidence_below_directive_floor_is_skipped(self):
        items = [{"text": "a", "subject": "s", "relation": "r", "object": "o", "confidence": 0.05}]
        worker = lw.LLMWorker(call_model=lambda model, prompt: json.dumps(items))
        _, _, directive = _spawn(ExtractionType.CLAIMS, confidence_floor=0.5)
        env = worker.run(directive, TEXT)
        self.assertEqual(env.nodes, [])
        self.assertEqual(env.traces[0].reason_code, "BELOW_DIRECTIVE_FLOOR")

    def test_max_results_caps_emitted_nodes_and_abstains_the_rest(self):
        items = [
            {"text": f"claim {i}", "subject": "s", "relation": "r", "object": f"o{i}",
             "confidence": 0.9}
            for i in range(3)
        ]
        worker = lw.LLMWorker(call_model=lambda model, prompt: json.dumps(items))
        _, _, directive = _spawn(ExtractionType.CLAIMS, max_results=2)
        env = worker.run(directive, TEXT)
        self.assertEqual(len(env.nodes), 2)
        abstain_traces = [t for t in env.traces if t.decision_type.value == "abstain"]
        self.assertEqual(len(abstain_traces), 1)
        self.assertEqual(abstain_traces[0].reason_code, "MAX_RESULTS_REACHED")

    def test_model_call_exception_fails_the_envelope_not_the_process(self):
        def boom(model, prompt):
            raise RuntimeError("network error")
        worker = lw.LLMWorker(call_model=boom)
        _, _, directive = _spawn(ExtractionType.CLAIMS)
        env = worker.run(directive, TEXT)
        self.assertEqual(env.worker_status, "failed")
        self.assertIn("network error", env.error)

    def test_malformed_json_response_fails_the_envelope(self):
        worker = lw.LLMWorker(call_model=lambda model, prompt: "not json")
        _, _, directive = _spawn(ExtractionType.CLAIMS)
        env = worker.run(directive, TEXT)
        self.assertEqual(env.worker_status, "failed")

    def test_unsupported_extraction_type_fails_cleanly(self):
        worker = lw.LLMWorker(call_model=lambda model, prompt: "[]")
        _, _, directive = _spawn(ExtractionType.METHODS)
        env = worker.run(directive, TEXT)
        self.assertEqual(env.worker_status, "failed")
        self.assertIn("methods", env.error)

    def test_default_call_model_is_used_when_none_injected(self):
        worker = lw.LLMWorker()
        self.assertIs(worker.call_model, lw._default_call_model)


class TestLLMWorkerEnvelopeIsAdmissible(unittest.TestCase):
    """
    The real point of this worker existing: its output must satisfy exactly
    the same envelope contract ReferenceWorker's does. WorkerSpawner.admit()
    doesn't know or care which worker produced an envelope.
    """

    def test_envelope_is_admitted_by_the_unmodified_spawner(self):
        items = [
            {"text": "Hierarchical orchestration reduces coordination overhead.",
             "subject": "hierarchical orchestration", "relation": "reduces",
             "object": "coordination overhead", "confidence": 0.87},
        ]
        worker = lw.LLMWorker(call_model=lambda model, prompt: json.dumps(items))
        spawner, graph, directive = _spawn(ExtractionType.CLAIMS)
        env = worker.run(directive, TEXT)
        result = spawner.admit(directive, env)
        self.assertTrue(result.admitted)
        self.assertEqual(result.nodes_admitted, 1)
        self.assertTrue(graph.validate().valid, graph.validate().to_dict())


class TestDefaultCallModel(unittest.TestCase):
    """Proves the real-call path's plumbing without a network call or API key."""

    def test_constructs_client_and_extracts_text_from_response(self):
        fake_block = MagicMock()
        fake_block.text = "[]"
        fake_message = MagicMock()
        fake_message.content = [fake_block]
        fake_client = MagicMock()
        fake_client.messages.create.return_value = fake_message

        fake_anthropic_module = MagicMock()
        fake_anthropic_module.Anthropic.return_value = fake_client

        with patch.dict("sys.modules", {"anthropic": fake_anthropic_module}):
            result = lw._default_call_model("claude-sonnet-5", "a prompt")

        self.assertEqual(result, "[]")
        fake_client.messages.create.assert_called_once()
        _, kwargs = fake_client.messages.create.call_args
        self.assertEqual(kwargs["model"], "claude-sonnet-5")
        self.assertEqual(kwargs["messages"], [{"role": "user", "content": "a prompt"}])


if __name__ == "__main__":
    unittest.main()
