"""
A lightweight in-memory governance simulation to demonstrate:
- proposal lifecycle (tentative -> governed -> committed)
- append-only canonical event store
- projections: canonical, tentative, shadow
- provenance and audit records
- versioning/stale-version protection
This is intentionally framework- and infra-free; everything is in-memory and deterministic for tests.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import uuid
import time

# Roles: 'agent', 'governor', 'system'

def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

@dataclass
class Event:
    event_id: str
    aggregate_id: str
    event_type: str
    timestamp: str
    actor_id: str
    actor_role: str
    payload: Dict[str, Any]
    provenance: Dict[str, Any]
    status: str  # 'committed'
    prev_version: int
    new_version: int


@dataclass
class Proposal:
    proposal_id: str
    proposer_id: str
    proposer_role: str
    aggregate_id: str
    proposed_payload: Dict[str, Any]
    status: str = "tentative"  # tentative | approved | rejected
    created_at: str = field(default_factory=now_iso)
    evidence: Optional[Dict[str, Any]] = None
    prev_version: int = 0


@dataclass
class DecisionRecord:
    decision_id: str
    proposal_id: str
    decider_id: str
    decider_role: str
    decision: str  # approve | deny
    rationale: str
    timestamp: str = field(default_factory=now_iso)


class AuditLog:
    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def record(self, entry: Dict[str, Any]):
        self.records.append(entry)


class InMemoryEventStore:
    """Append-only event store. Only governance/commit path may append committed events."""
    def __init__(self):
        self.events: List[Event] = []

    def append_committed(self, event: Event, actor_role: str):
        # Enforce ACL: only 'governor' or 'system' can append committed events
        if actor_role not in ("governor", "system"):
            raise PermissionError("Only governance/system may append committed events")
        self.events.append(event)

    def all_events(self) -> List[Event]:
        return list(self.events)


class CanonicalState:
    """Materialized state derived from events. Maintains version number."""
    def __init__(self):
        self.state: Dict[str, Any] = {}
        self.version: int = 0
        self.history: List[Event] = []

    def apply_event(self, event: Event):
        # apply the payload onto state (simple key overwrite semantics)
        for k, v in event.payload.items():
            self.state[k] = v
        self.version = event.new_version
        self.history.append(event)

    def snapshot(self) -> Dict[str, Any]:
        return dict(self.state)


class ProposalStore:
    def __init__(self):
        self.proposals: Dict[str, Proposal] = {}

    def create_proposal(self, proposer_id: str, proposer_role: str, aggregate_id: str, proposed_payload: Dict[str, Any], prev_version: int, evidence: Optional[Dict[str, Any]] = None) -> Proposal:
        pid = str(uuid.uuid4())
        p = Proposal(
            proposal_id=pid,
            proposer_id=proposer_id,
            proposer_role=proposer_role,
            aggregate_id=aggregate_id,
            proposed_payload=proposed_payload,
            evidence=evidence,
            prev_version=prev_version,
        )
        self.proposals[pid] = p
        return p

    def get(self, proposal_id: str) -> Proposal:
        return self.proposals[proposal_id]


class GovernanceService:
    """Makes decisions. In this simple model, only role 'governor' may approve."""
    def __init__(self, audit: AuditLog):
        self.audit = audit

    def decide(self, proposal: Proposal, decider_id: str, decider_role: str, approve: bool, rationale: str = "") -> DecisionRecord:
        dr = DecisionRecord(
            decision_id=str(uuid.uuid4()),
            proposal_id=proposal.proposal_id,
            decider_id=decider_id,
            decider_role=decider_role,
            decision="approve" if approve else "deny",
            rationale=rationale,
        )
        # record audit
        self.audit.record({
            "type": "decision",
            "decision_id": dr.decision_id,
            "proposal_id": proposal.proposal_id,
            "decider_id": decider_id,
            "decider_role": decider_role,
            "decision": dr.decision,
            "rationale": rationale,
            "timestamp": dr.timestamp,
        })

        if approve:
            if decider_role != "governor":
                # insufficient authority
                proposal.status = "tentative"
                return dr
            proposal.status = "approved"
        else:
            proposal.status = "rejected"
        return dr


class CommitService:
    def __init__(self, event_store: InMemoryEventStore, canonical: CanonicalState, audit: AuditLog):
        self.event_store = event_store
        self.canonical = canonical
        self.audit = audit

    def commit(self, proposal: Proposal, decision: DecisionRecord, committer_id: str, committer_role: str) -> Event:
        # Only commit if proposal approved
        if proposal.status != "approved":
            raise RuntimeError("Proposal not approved")
        # Only governance/system may commit
        if committer_role not in ("governor", "system"):
            raise PermissionError("Only governance/system may commit events")
        # Stale version check
        expected_prev = proposal.prev_version
        if expected_prev != self.canonical.version:
            raise RuntimeError("REJECT_STALE_VERSION")
        new_version = self.canonical.version + 1
        e = Event(
            event_id=str(uuid.uuid4()),
            aggregate_id=proposal.aggregate_id,
            event_type="Update",
            timestamp=now_iso(),
            actor_id=committer_id,
            actor_role=committer_role,
            payload=proposal.proposed_payload,
            provenance={
                "proposal_id": proposal.proposal_id,
                "decision_id": decision.decision_id,
                "decider_id": decision.decider_id,
                "decider_role": decision.decider_role,
                "rationale": decision.rationale,
                "evidence": proposal.evidence,
            },
            status="committed",
            prev_version=self.canonical.version,
            new_version=new_version,
        )
        # append to event store
        self.event_store.append_committed(e, actor_role=committer_role)
        # apply to canonical state
        self.canonical.apply_event(e)
        # audit
        self.audit.record({
            "type": "commit",
            "event_id": e.event_id,
            "proposal_id": proposal.proposal_id,
            "committer_id": committer_id,
            "committer_role": committer_role,
            "prev_version": e.prev_version,
            "new_version": e.new_version,
            "timestamp": e.timestamp,
        })
        return e


class ProjectionManager:
    """Provides canonical, tentative, and shadow projections."""
    def __init__(self, canonical: CanonicalState, proposal_store: ProposalStore):
        self.canonical = canonical
        self.proposal_store = proposal_store
        # shadows are stored separately keyed by name
        self.shadows: Dict[str, Dict[str, Any]] = {}

    def canonical_projection(self) -> Dict[str, Any]:
        return self.canonical.snapshot()

    def tentative_projection(self) -> Dict[str, Any]:
        # start from canonical and overlay all tentative proposals (last-write-wins by proposal creation order)
        out = dict(self.canonical.snapshot())
        for p in self.proposal_store.proposals.values():
            if p.status == "tentative":
                for k, v in p.proposed_payload.items():
                    out[k] = v
        return out

    def shadow_create(self, name: str, base: Optional[Dict[str, Any]] = None):
        self.shadows[name] = dict(base or self.canonical.snapshot())

    def shadow_update(self, name: str, payload: Dict[str, Any]):
        if name not in self.shadows:
            raise KeyError("shadow not found")
        self.shadows[name].update(payload)

    def shadow_projection(self, name: str) -> Dict[str, Any]:
        if name not in self.shadows:
            raise KeyError("shadow not found")
        return dict(self.shadows[name])


# helper to initialize a small scenario
def make_environment(initial_state: Dict[str, Any] = None):
    event_store = InMemoryEventStore()
    canonical = CanonicalState()
    audit = AuditLog()
    proposal_store = ProposalStore()
    governance = GovernanceService(audit=audit)
    committer = CommitService(event_store=event_store, canonical=canonical, audit=audit)
    projector = ProjectionManager(canonical=canonical, proposal_store=proposal_store)

    # create initial event to seed state if provided
    if initial_state:
        e = Event(
            event_id=str(uuid.uuid4()),
            aggregate_id="root",
            event_type="Init",
            timestamp=now_iso(),
            actor_id="system",
            actor_role="system",
            payload=initial_state,
            provenance={"system_init": True},
            status="committed",
            prev_version=0,
            new_version=1,
        )
        event_store.append_committed(e, actor_role="system")
        canonical.apply_event(e)
        audit.record({"type": "init", "event_id": e.event_id, "timestamp": e.timestamp})

    return {
        "event_store": event_store,
        "canonical": canonical,
        "audit": audit,
        "proposal_store": proposal_store,
        "governance": governance,
        "committer": committer,
        "projector": projector,
    }
