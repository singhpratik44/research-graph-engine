#!/usr/bin/env python3
"""
Test suite for arxiv_ingest.py. The live GET can't be exercised here (this
session's egress policy blocks arxiv.org/export.arxiv.org outright -- see the
module docstring), so these tests inject a saved sample Atom response,
structured the same way the real arXiv API documents its output
(https://info.arxiv.org/help/api/index.html), and prove the parsing,
conversion, and idempotent-append logic against it.
"""

import unittest
from unittest.mock import Mock

from research_graph_schema import NodeType, ResearchGraph
import arxiv_ingest as ingest

# A representative two-entry response in the arXiv API's documented Atom shape.
# One entry has two authors and a trailing version suffix on its id (v2), the
# other has one author and no version suffix -- both forms occur in practice.
SAMPLE_ATOM_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <opensearch:totalResults>2</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/2605.03042v2</id>
    <updated>2026-05-06T00:00:00Z</updated>
    <published>2026-05-05T00:00:00Z</published>
    <title>ARIS: Autonomous Research via Adversarial Multi-Agent
  Collaboration</title>
    <summary>  We present ARIS, a research harness that coordinates ML
  research workflows through cross-model adversarial collaboration.
  </summary>
    <author><name>Jane Researcher</name></author>
    <author><name>Alex Collaborator</name></author>
    <link href="http://arxiv.org/abs/2605.03042v2" rel="alternate" type="text/html"/>
    <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom" term="cs.AI"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2606.99999</id>
    <updated>2026-06-10T00:00:00Z</updated>
    <published>2026-06-10T00:00:00Z</published>
    <title>A Synthetic Test Paper With No Version Suffix</title>
    <summary>A short abstract for parser testing purposes.</summary>
    <author><name>Solo Author</name></author>
    <link href="http://arxiv.org/abs/2606.99999" rel="alternate" type="text/html"/>
  </entry>
</feed>
"""

EMPTY_ATOM_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>0</opensearch:totalResults>
</feed>
"""


def _fake_get(response_text: str, status_code: int = 200):
    resp = Mock()
    resp.text = response_text
    resp.status_code = status_code
    resp.raise_for_status = Mock() if status_code == 200 else Mock(
        side_effect=Exception(f"HTTP {status_code}"))
    return Mock(return_value=resp)


class TestParseArxivAtom(unittest.TestCase):
    def test_parses_both_entries(self):
        entries = ingest.parse_arxiv_atom(SAMPLE_ATOM_RESPONSE)
        self.assertEqual(len(entries), 2)

    def test_strips_version_suffix_from_id(self):
        entries = ingest.parse_arxiv_atom(SAMPLE_ATOM_RESPONSE)
        self.assertEqual(entries[0].arxiv_id, "2605.03042")

    def test_id_without_version_suffix_still_parses(self):
        entries = ingest.parse_arxiv_atom(SAMPLE_ATOM_RESPONSE)
        self.assertEqual(entries[1].arxiv_id, "2606.99999")

    def test_title_whitespace_is_normalized(self):
        entries = ingest.parse_arxiv_atom(SAMPLE_ATOM_RESPONSE)
        self.assertEqual(entries[0].title,
                         "ARIS: Autonomous Research via Adversarial Multi-Agent Collaboration")

    def test_published_date_truncated_to_date_only(self):
        entries = ingest.parse_arxiv_atom(SAMPLE_ATOM_RESPONSE)
        self.assertEqual(entries[0].published, "2026-05-05")

    def test_multiple_authors_parsed_in_order(self):
        entries = ingest.parse_arxiv_atom(SAMPLE_ATOM_RESPONSE)
        self.assertEqual(entries[0].authors, ["Jane Researcher", "Alex Collaborator"])

    def test_empty_feed_yields_no_entries(self):
        self.assertEqual(ingest.parse_arxiv_atom(EMPTY_ATOM_RESPONSE), [])


class TestEntryToPaperNode(unittest.TestCase):
    def test_node_id_derived_from_arxiv_id(self):
        entries = ingest.parse_arxiv_atom(SAMPLE_ATOM_RESPONSE)
        node = ingest.entry_to_paper_node(entries[0])
        self.assertEqual(node.id, "paper_2605_03042")

    def test_node_is_schema_valid(self):
        from research_graph_schema import validate_node
        entries = ingest.parse_arxiv_atom(SAMPLE_ATOM_RESPONSE)
        for entry in entries:
            node = ingest.entry_to_paper_node(entry)
            result = validate_node(node)
            self.assertTrue(result.valid, [e.message for e in result.errors])

    def test_provenance_sourced_to_its_own_arxiv_id(self):
        entries = ingest.parse_arxiv_atom(SAMPLE_ATOM_RESPONSE)
        node = ingest.entry_to_paper_node(entries[0])
        self.assertEqual(node.provenance.source_paper, "2605.03042")
        self.assertFalse(node.provenance.human_reviewed)


class TestFetchArxivEntries(unittest.TestCase):
    def test_injected_http_get_is_used_instead_of_network(self):
        fake_get = _fake_get(SAMPLE_ATOM_RESPONSE)
        entries = ingest.fetch_arxiv_entries("all:test", max_results=2, http_get=fake_get)
        self.assertEqual(len(entries), 2)
        fake_get.assert_called_once()
        called_url = fake_get.call_args[0][0]
        self.assertEqual(called_url, ingest.ARXIV_API_URL)

    def test_query_params_forwarded(self):
        fake_get = _fake_get(SAMPLE_ATOM_RESPONSE)
        ingest.fetch_arxiv_entries("all:orchestration", max_results=3, http_get=fake_get)
        params = fake_get.call_args.kwargs["params"]
        self.assertEqual(params["search_query"], "all:orchestration")
        self.assertEqual(params["max_results"], 3)

    def test_http_error_propagates(self):
        fake_get = _fake_get("", status_code=500)
        with self.assertRaises(Exception):
            ingest.fetch_arxiv_entries("all:test", http_get=fake_get)


class TestIngestArxiv(unittest.TestCase):
    def test_adds_new_papers_to_graph(self):
        graph = ResearchGraph()
        fake_get = _fake_get(SAMPLE_ATOM_RESPONSE)
        added = ingest.ingest_arxiv(graph, "all:test", http_get=fake_get)
        self.assertEqual(len(added), 2)
        self.assertEqual(len(graph.nodes), 2)
        self.assertTrue(all(n.type == NodeType.PAPER.value for n in graph.nodes))

    def test_idempotent_against_rerunning_same_query(self):
        graph = ResearchGraph()
        fake_get = _fake_get(SAMPLE_ATOM_RESPONSE)
        ingest.ingest_arxiv(graph, "all:test", http_get=fake_get)
        second_added = ingest.ingest_arxiv(graph, "all:test", http_get=_fake_get(SAMPLE_ATOM_RESPONSE))
        self.assertEqual(second_added, [])
        self.assertEqual(len(graph.nodes), 2)

    def test_skips_only_the_paper_already_present(self):
        graph = ResearchGraph()
        first_get = _fake_get(SAMPLE_ATOM_RESPONSE)
        ingest.ingest_arxiv(graph, "all:test", max_results=1, http_get=_fake_get(
            '<feed xmlns="http://www.w3.org/2005/Atom">'
            '<entry><id>http://arxiv.org/abs/2605.03042v2</id>'
            '<published>2026-05-05T00:00:00Z</published>'
            '<title>ARIS</title><summary>s</summary>'
            '<link href="http://arxiv.org/abs/2605.03042v2" rel="alternate"/></entry>'
            '</feed>'
        ))
        self.assertEqual(len(graph.nodes), 1)
        added = ingest.ingest_arxiv(graph, "all:test", http_get=first_get)
        self.assertEqual({n.id for n in added}, {"paper_2606_99999"})
        self.assertEqual(len(graph.nodes), 2)


class TestUndocumentedSourceStubs(unittest.TestCase):
    def test_huggingface_stub_raises_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            ingest.fetch_huggingface_papers()

    def test_langchain_blog_stub_raises_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            ingest.fetch_langchain_blog_posts()


if __name__ == "__main__":
    unittest.main()
