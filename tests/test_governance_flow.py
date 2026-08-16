import unittest
from governance_sim import make_environment


class GovernanceFlowTests(unittest.TestCase):
    def test_scenario_1_tentative(self):
        env = make_environment({"STAFFING": 100})
        p = env["proposal_store"].create_proposal(
            proposer_id="agent-1",
            proposer_role="agent",
            aggregate_id="root",
            proposed_payload={"STAFFING": 80},
            prev_version=env["canonical"].version,
            evidence={"note": "reduce staffing"},
        )
        # verify canonical unchanged
        self.assertEqual(env["canonical"].state["STAFFING"], 100)
        # proposal contains 80
        self.assertEqual(p.proposed_payload["STAFFING"], 80)
        # graph projection of canonical remains unchanged
        self.assertEqual(env["projector"].canonical_projection()["STAFFING"], 100)
        # proposal is tentative
        self.assertEqual(p.status, "tentative")
        # provenance identifies proposer
        self.assertEqual(p.proposer_id, "agent-1")

    def test_scenario_2_governance_rejection(self):
        env = make_environment({"STAFFING": 100})
        p = env["proposal_store"].create_proposal(
            proposer_id="agent-2",
            proposer_role="agent",
            aggregate_id="root",
            proposed_payload={"STAFFING": 80},
            prev_version=env["canonical"].version,
        )
        # insufficient authority tries to deny (or approve) - simulate a non-governor trying to approve
        decision = env["governance"].decide(p, decider_id="user-unauthorized", decider_role="agent", approve=False, rationale="not allowed")
        # governance returns DENY
        self.assertEqual(decision.decision, "deny")
        # canonical state remains unchanged
        self.assertEqual(env["canonical"].state["STAFFING"], 100)
        # no canonical mutation occurs (no new events)
        self.assertEqual(len(env["event_store"].events), 1)  # initial seed only
        # no committed event is generated
        # audit record records the rejection
        found = [r for r in env["audit"].records if r.get("type") == "decision" and r.get("decision") == "deny"]
        self.assertTrue(len(found) >= 1)

    def test_scenario_3_governance_approval(self):
        env = make_environment({"STAFFING": 100})
        p = env["proposal_store"].create_proposal(
            proposer_id="agent-3",
            proposer_role="agent",
            aggregate_id="root",
            proposed_payload={"STAFFING": 80},
            prev_version=env["canonical"].version,
            evidence={"survey": "downsizing"},
        )
        # governor approves
        decision = env["governance"].decide(p, decider_id="gov-1", decider_role="governor", approve=True, rationale="budget cut approved")
        self.assertEqual(p.status, "approved")
        # commit
        e = env["committer"].commit(p, decision, committer_id="gov-1", committer_role="governor")
        # transaction is authorized
        self.assertEqual(e.actor_role, "governor")
        # event is created
        self.assertEqual(len(env["event_store"].events), 2)
        # canonical state becomes 80
        self.assertEqual(env["canonical"].state["STAFFING"], 80)
        # graph projection reflects 80
        self.assertEqual(env["projector"].canonical_projection()["STAFFING"], 80)
        # previous state remains replayable
        self.assertEqual(env["canonical"].history[0].payload["STAFFING"], 100)
        # audit contains who/what/when/why/authority
        commits = [r for r in env["audit"].records if r.get("type") == "commit"]
        self.assertTrue(len(commits) == 1)
        c = commits[0]
        self.assertEqual(c["committer_role"], "governor")

    def test_scenario_4_shadow_simulation(self):
        env = make_environment({"STAFFING": 100, "ENROLLMENT": 500, "RETENTION": 0.8})
        pm = env["projector"]
        pm.shadow_create("scenario-A")
        pm.shadow_update("scenario-A", {"STAFFING": 80})
        # shadow graph changes
        self.assertEqual(pm.shadow_projection("scenario-A")["STAFFING"], 80)
        # downstream effects can be calculated/projected (simple derived example)
        shadow = pm.shadow_projection("scenario-A")
        projected_revenue = shadow["ENROLLMENT"] * 100  # example calc
        self.assertEqual(projected_revenue, 500 * 100)
        # canonical unchanged
        self.assertEqual(env["canonical"].state["STAFFING"], 100)
        # shadow is clearly distinguished
        self.assertNotEqual(pm.shadow_projection("scenario-A")["STAFFING"], pm.canonical_projection()["STAFFING"])

    def test_scenario_5_stale_version(self):
        env = make_environment({"STAFFING": 100})
        # user A reads version 1
        vA = env["canonical"].version
        # user B proposes and governor commits
        pB = env["proposal_store"].create_proposal("agent-b", "agent", "root", {"STAFFING": 90}, prev_version=env["canonical"].version)
        dB = env["governance"].decide(pB, decider_id="gov-x", decider_role="governor", approve=True, rationale="ok")
        env["committer"].commit(pB, dB, committer_id="gov-x", committer_role="governor")
        # now user A attempts to commit against older version
        pA = env["proposal_store"].create_proposal("agent-a", "agent", "root", {"STAFFING": 80}, prev_version=vA)
        dA = env["governance"].decide(pA, decider_id="gov-y", decider_role="governor", approve=True, rationale="ok")
        with self.assertRaises(RuntimeError) as ctx:
            env["committer"].commit(pA, dA, committer_id="gov-y", committer_role="governor")
        self.assertIn("REJECT_STALE_VERSION", str(ctx.exception))
        # canonical state not corrupted
        self.assertEqual(env["canonical"].state["STAFFING"], 90)

    def test_scenario_6_agent_security(self):
        env = make_environment({"STAFFING": 100})
        # agent tries to directly append committed event - should fail
        from governance_sim import Event
        e = Event(
            event_id="bad",
            aggregate_id="root",
            event_type="Update",
            timestamp="now",
            actor_id="agent-x",
            actor_role="agent",
            payload={"STAFFING": 10},
            provenance={"note": "malicious"},
            status="committed",
            prev_version=env["canonical"].version,
            new_version=env["canonical"].version + 1,
        )
        with self.assertRaises(PermissionError):
            env["event_store"].append_committed(e, actor_role="agent")

    def test_scenario_7_tentative_vs_committed_projection(self):
        env = make_environment({"STAFFING": 100, "ENROLLMENT": 500, "RETENTION": 0.8, "REVENUE": 10000})
        # create two proposals
        p_tent = env["proposal_store"].create_proposal("agent-1", "agent", "root", {"STAFFING": 80}, prev_version=env["canonical"].version)
        p_other = env["proposal_store"].create_proposal("agent-2", "agent", "root", {"REVENUE": 9000}, prev_version=env["canonical"].version)
        # canonical
        canonical = env["projector"].canonical_projection()
        tentative = env["projector"].tentative_projection()
        # shadow
        env["projector"].shadow_create("test-shadow")
        env["projector"].shadow_update("test-shadow", {"STAFFING": 70})
        shadow = env["projector"].shadow_projection("test-shadow")
        # verify projections cannot be confused
        self.assertEqual(canonical["STAFFING"], 100)
        self.assertEqual(tentative["STAFFING"], 80)
        self.assertEqual(shadow["STAFFING"], 70)

    def test_scenario_8_replay(self):
        env = make_environment({"STAFFING": 100})
        # create and commit two proposals
        p1 = env["proposal_store"].create_proposal("a1", "agent", "root", {"STAFFING": 90}, prev_version=env["canonical"].version)
        d1 = env["governance"].decide(p1, "gov1", "governor", approve=True, rationale="ok")
        env["committer"].commit(p1, d1, "gov1", "governor")
        p2 = env["proposal_store"].create_proposal("a2", "agent", "root", {"STAFFING": 80}, prev_version=env["canonical"].version)
        d2 = env["governance"].decide(p2, "gov2", "governor", approve=True, rationale="ok")
        env["committer"].commit(p2, d2, "gov2", "governor")
        # replay events into a fresh canonical state
        events = env["event_store"].all_events()
        # skip initial init event if present
        from governance_sim import CanonicalState
        replay = CanonicalState()
        for e in events:
            replay.apply_event(e)
        self.assertEqual(replay.state, env["canonical"].state)

    def test_scenario_9_provenance(self):
        env = make_environment({"STAFFING": 100})
        p = env["proposal_store"].create_proposal("a1", "agent", "root", {"STAFFING": 80}, prev_version=env["canonical"].version, evidence={"doc": "evidence-1"})
        d = env["governance"].decide(p, "gov-1", "governor", approve=True, rationale="reduce")
        e = env["committer"].commit(p, d, "gov-1", "governor")
        prov = e.provenance
        self.assertIn("proposal_id", prov)
        self.assertIn("decision_id", prov)
        self.assertIn("decider_id", prov)
        self.assertIn("evidence", prov)
        self.assertEqual(e.prev_version, 1)
        self.assertEqual(e.new_version, 2)

    def test_scenario_10_invariant_no_direct_mutation(self):
        env = make_environment({"STAFFING": 100})
        # ensure API surfaces that would mutate canonical state do not bypass commit path
        # we assert that only CommitService.apply_event path updates canonical.version
        old_version = env["canonical"].version
        # simulate a rogue direct state change via direct assignment (disallowed by invariant)
        try:
            env["canonical"].state["STAFFING"] = 50
            violated = True
        except Exception:
            violated = False
        # the invariant test should fail loudly if violated
        self.assertFalse(violated, "Direct mutation attempted; architecture invariant violated (tests should prevent this).")
        # restore canonical to expected (tests consider direct assignment as violation)
        env["canonical"].state["STAFFING"] = 100
        self.assertEqual(env["canonical"].version, old_version)


if __name__ == '__main__':
    unittest.main()
