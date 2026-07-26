#!/usr/bin/env python3
"""
Phase 10: Live ingestion -- arXiv (item 3 of the portfolio brief, arXiv slice)

arXiv publishes a real, public, unauthenticated API (export.arxiv.org/api/query,
documented at https://info.arxiv.org/help/api/index.html) that returns an Atom
feed. This module calls it for real and turns each entry into a schema-
conforming PAPER node, ready to hand to WorkerSpawner the same way
literature_corpus.py's hand-curated papers are.

Hugging Face Papers and the LangChain Blog do NOT have an equivalent stable,
documented public API (no versioned JSON/Atom endpoint, no auth-free contract
guaranteed not to break) -- see fetch_huggingface_papers/fetch_langchain_blog_posts
below for why those are deliberately left as stubs rather than screen-scraped.

NETWORK NOTE: in the sandbox this was developed in, the egress policy blocks
arxiv.org/export.arxiv.org outright (403 at the proxy, before any HTTP request
lands) -- confirmed, not routed around. fetch_arxiv_entries() takes an
injectable `http_get` so the parsing/conversion logic is fully tested here
against a saved sample response; the only untested part is the live GET
itself, which needs the host allowlisted to run.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, List, Optional

import requests

from research_graph_schema import Node, NodeType, Provenance, ExtractionMethod, ResearchGraph

ARXIV_API_URL = "http://export.arxiv.org/api/query"
_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ArxivEntry:
    arxiv_id: str          # e.g. "2605.03042"
    title: str
    summary: str
    published: str         # e.g. "2026-05-05"
    url: str
    authors: List[str]


def _entry_id_to_arxiv_id(atom_id: str) -> str:
    """'http://arxiv.org/abs/2605.03042v1' -> '2605.03042'"""
    tail = atom_id.rsplit("/", 1)[-1]
    return tail.split("v")[0] if "v" in tail else tail


def parse_arxiv_atom(xml_text: str) -> List[ArxivEntry]:
    """Parses an arXiv API Atom response into ArxivEntry records. No network here."""
    root = ET.fromstring(xml_text)
    entries = []
    for entry_el in root.findall("atom:entry", _ATOM_NS):
        atom_id = (entry_el.findtext("atom:id", default="", namespaces=_ATOM_NS) or "").strip()
        title = " ".join((entry_el.findtext("atom:title", default="", namespaces=_ATOM_NS) or "").split())
        summary = " ".join((entry_el.findtext("atom:summary", default="", namespaces=_ATOM_NS) or "").split())
        published_raw = (entry_el.findtext("atom:published", default="", namespaces=_ATOM_NS) or "").strip()
        published = published_raw[:10] if published_raw else ""
        authors = [
            (a.findtext("atom:name", default="", namespaces=_ATOM_NS) or "").strip()
            for a in entry_el.findall("atom:author", _ATOM_NS)
        ]
        url = ""
        for link_el in entry_el.findall("atom:link", _ATOM_NS):
            if link_el.get("rel") == "alternate":
                url = link_el.get("href", "")
                break
        if not atom_id or not title:
            continue
        entries.append(ArxivEntry(
            arxiv_id=_entry_id_to_arxiv_id(atom_id),
            title=title,
            summary=summary,
            published=published,
            url=url or atom_id,
            authors=[a for a in authors if a],
        ))
    return entries


def fetch_arxiv_entries(
    query: str,
    max_results: int = 10,
    http_get: Callable[..., "requests.Response"] = requests.get,
) -> List[ArxivEntry]:
    """
    Real call to the arXiv API. `http_get` is injectable so tests can supply a
    saved response without hitting the network -- production code just uses
    the default (requests.get).
    """
    resp = http_get(
        ARXIV_API_URL,
        params={"search_query": query, "start": 0, "max_results": max_results,
                "sortBy": "submittedDate", "sortOrder": "descending"},
        timeout=30,
        headers={"User-Agent": "research-graph-engine/1.0 (ingestion worker)"},
    )
    resp.raise_for_status()
    return parse_arxiv_atom(resp.text)


def entry_to_paper_node(entry: ArxivEntry) -> Node:
    """Same shape as the hand-curated papers in literature_corpus.py: id `paper_<arxiv_id>`,
    provenance sourced to the paper's own id, confidence 1.0 (metadata, not extracted content)."""
    node_id = f"paper_{entry.arxiv_id.replace('.', '_')}"
    return Node(
        id=node_id,
        type=NodeType.PAPER.value,
        label=entry.title,
        provenance=Provenance(
            source_paper=entry.arxiv_id,
            extraction_method=ExtractionMethod.METADATA.value,
            confidence=1.0,
            extracted_at=_now(),
            human_reviewed=False,
            review_notes="Ingested from the arXiv API.",
        ),
        properties={
            "title": entry.title,
            "url": entry.url,
            "published": entry.published,
            "authors": entry.authors,
        },
    )


def ingest_arxiv(
    graph: ResearchGraph,
    query: str,
    max_results: int = 10,
    http_get: Callable[..., "requests.Response"] = requests.get,
) -> List[Node]:
    """
    Fetches entries for `query`, converts each to a PAPER node, and appends the
    ones not already in `graph` (by node id) -- idempotent against re-running
    the same query. Returns only the newly added nodes.
    """
    existing_ids = set(graph.index())
    added: List[Node] = []
    for entry in fetch_arxiv_entries(query, max_results, http_get):
        node = entry_to_paper_node(entry)
        if node.id in existing_ids:
            continue
        graph.nodes.append(node)
        existing_ids.add(node.id)
        added.append(node)
    return added


def fetch_huggingface_papers():
    """
    NOT IMPLEMENTED. huggingface.co/papers is a web page backed by an internal,
    undocumented endpoint -- there is no versioned public API contract, so any
    scraper here would be reverse-engineering a page that can change without
    notice. To wire this up for real: get a stable data source first (an
    official HF API scope for papers, or an RSS/Atom feed if one is ever
    published), then mirror fetch_arxiv_entries()'s shape -- inject the HTTP
    client, parse into a small dataclass, convert to a PAPER node.
    """
    raise NotImplementedError(
        "Hugging Face Papers has no documented public API; see this function's docstring."
    )


def fetch_langchain_blog_posts():
    """
    NOT IMPLEMENTED. blog.langchain.com has no published RSS/Atom/JSON feed as
    of this writing -- ingesting it for real means HTML scraping, which is
    fragile (any markup change silently breaks it) and was explicitly out of
    scope for this pass. To wire this up for real: confirm whether an RSS feed
    exists (check /rss.xml, /feed), and if not, scope a scraper against a
    pinned snapshot of the page structure with its own regression test.
    """
    raise NotImplementedError(
        "The LangChain blog has no stable feed to ingest from; see this function's docstring."
    )


if __name__ == "__main__":
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "all:knowledge graph provenance"
    graph = ResearchGraph()
    added = ingest_arxiv(graph, query, max_results=5)
    for node in added:
        print(f"{node.id}: {node.properties['title']}")
