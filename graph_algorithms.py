#!/usr/bin/env python3
"""
Small, dependency-free graph algorithms shared across modules that each need
their own notion of "nodes with directed edges" -- ResearchGraph's
extraction_job BLOCKED_BY edges (graph_queries.py) and task_graph.py's
TaskEdge DEPENDS_ON edges both reduce to the same adjacency-dict cycle
detection problem. One implementation, so a bug fixed in one place doesn't
need fixing twice.
"""

from typing import Dict, List


def detect_cycles(adjacency: Dict[str, List[str]]) -> List[List[str]]:
    """
    Standard three-color DFS cycle detection. `adjacency` maps a node id to
    the list of node ids it points to. Returns each cycle found as a closed
    list of node ids (first id repeated at the end); an empty list means the
    graph is acyclic. Not exhaustive over every possible cycle in a graph with
    multiple entry points into the same cycle -- sufficient for "does this
    graph deadlock," not for enumerating every cycle a graph could contain.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color: Dict[str, int] = {}
    cycles: List[List[str]] = []

    def visit(node: str, path: List[str]) -> None:
        color[node] = GRAY
        path.append(node)
        for neighbor in adjacency.get(node, []):
            state = color.get(neighbor, WHITE)
            if state == WHITE:
                visit(neighbor, path)
            elif state == GRAY:
                cycle_start = path.index(neighbor)
                cycles.append(path[cycle_start:] + [neighbor])
        path.pop()
        color[node] = BLACK

    for node_id in list(adjacency):
        if color.get(node_id, WHITE) == WHITE:
            visit(node_id, [])

    return cycles
