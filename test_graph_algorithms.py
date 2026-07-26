#!/usr/bin/env python3
"""
Test suite for graph_algorithms.py, the shared cycle-detection primitive
graph_queries.py and task_graph.py both build on.
"""

import unittest

import graph_algorithms as ga


class TestDetectCycles(unittest.TestCase):
    def test_empty_adjacency_has_no_cycles(self):
        self.assertEqual(ga.detect_cycles({}), [])

    def test_acyclic_chain_has_no_cycles(self):
        self.assertEqual(ga.detect_cycles({"a": ["b"], "b": ["c"]}), [])

    def test_direct_two_cycle_detected(self):
        cycles = ga.detect_cycles({"a": ["b"], "b": ["a"]})
        self.assertEqual(len(cycles), 1)
        self.assertEqual(set(cycles[0]), {"a", "b"})
        self.assertEqual(cycles[0][0], cycles[0][-1])

    def test_longer_cycle_detected(self):
        cycles = ga.detect_cycles({"a": ["b"], "b": ["c"], "c": ["a"]})
        self.assertEqual(len(cycles), 1)
        self.assertEqual(set(cycles[0]), {"a", "b", "c"})

    def test_self_loop_detected(self):
        self.assertEqual(ga.detect_cycles({"a": ["a"]}), [["a", "a"]])

    def test_disconnected_acyclic_components_have_no_cycles(self):
        self.assertEqual(ga.detect_cycles({"a": ["b"], "x": ["y"]}), [])

    def test_branching_dag_has_no_cycles(self):
        # a -> b, a -> c, b -> d, c -> d (diamond) is acyclic even though d
        # has two incoming paths.
        adjacency = {"a": ["b", "c"], "b": ["d"], "c": ["d"]}
        self.assertEqual(ga.detect_cycles(adjacency), [])

    def test_node_referenced_only_as_a_target_is_handled(self):
        # "b" never appears as a key, only as a value -- must not KeyError.
        self.assertEqual(ga.detect_cycles({"a": ["b"]}), [])


if __name__ == "__main__":
    unittest.main()
