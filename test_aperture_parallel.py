import unittest
from aperture_parallel import Task, run

class SchedulerTests(unittest.TestCase):
    def test_dependencies(self):
        order = []
        def work(t):
            order.append(t.id)
            return t.id
        result = run([Task("b","dev",("a",)), Task("a","dev")], {"dev":work})
        self.assertEqual(order, ["a","b"])
        self.assertEqual(result["b"].status, "completed")

    def test_approval_and_descendants(self):
        tasks = [Task("send","sales",requires_approval=True),Task("follow","sales",("send",))]
        result = run(tasks,{"sales":lambda t: t.id})
        self.assertEqual(result["send"].status,"held")
        self.assertEqual(result["follow"].status,"blocked")

    def test_failure(self):
        def fail(t):
            raise RuntimeError("worker failure")
        result = run([Task("a","ops"),Task("b","ops",("a",))],{"ops":fail})
        self.assertEqual(result["a"].status,"failed")
        self.assertEqual(result["b"].status,"blocked")

    def test_cycle(self):
        with self.assertRaises(ValueError):
            run([Task("a","ops",("b",)),Task("b","ops",("a",))],{"ops":lambda t: None})

    def test_duplicate(self):
        with self.assertRaises(ValueError):
            run([Task("a","ops"),Task("a","ops")],{"ops":lambda t: None})

if __name__ == "__main__":
    unittest.main()
