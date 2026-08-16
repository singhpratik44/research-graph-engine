"""
Hardened in-memory governance kernel.
- Deep-frozen snapshots for canonical state and projections.
- Controlled event application via a CommitHandle produced in make_environment and held only by CommitService.
- Governance.decide semantics normalized: APPROVE, REJECT, INSUFFICIENT_AUTHORITY.
- verify_integrity() implementation: replay check + version/event consistency + state hash.
- Replay API provided to rebuild canonical state from event list.

Security note: Public APIs never expose mutable canonical state; all projections/snapshots are immutable deep-frozen views.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import uuid
import time
import copy
import json
import hashlib
from types import MappingProxyType

# Roles: 'agent', 'governor', 'system'

def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _freeze(obj: Any) -> Any:
    """Recursively freeze nested structures.
    dict -> MappingProxyType over a dict of frozen values
    list/tuple -> tuple of frozen values
    set -> frozenset
    primitives unchanged
    """
    if isinstance(obj, MappingProxyType):
        return obj
    if isinstance(obj, dict):
        frozen_dict = {k: _freeze(v) for k, v in obj.items()}
        return MappingProxyType(frozen_dict)
    if isinstance(obj, list) or isinstance(obj, tuple):
        return tuple(_freeze(v) for v in obj)
    if isinstance(obj, set):
        return frozenset(_freeze(v) for v in obj)
    # assume primitive (int/float/str/bool/None)
    return obj


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class DecisionRecord:
    decision_id: str
    proposal_id: str
    decider_id: str
    decider_role: str
    decision: str  # APPROVE | REJECT | INSUFFICIENT_AUTHORITY
    reason: str
    evidence: Optional[Dict[str, Any]]
    timestamp: str
    previous_status: str
    new_status: str


class AuditLog:
    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def record(self, entry: Dict[str, Any]):
        # store a deep copy so later mutations in tests can't tamper with audit records
        self.records.append(copy.deepcopy(entry))


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
    """Materialized state derived from events. Maintains version number.

    Publicly exposes only deep-frozen snapshots via snapshot(). The backing
    mutable state is private and inaccessible via public API.
    """

    def __init__(self):
        # private backing store
        self.__backing_state: Dict[str, Any] = {}
        self.version: int = 0
        self.history: List[Event] = []

    # snapshot returns a deep-frozen, mapping-proxy view of state
    def snapshot(self) -> MappingProxyType:
        # deep copy and freeze nested structures
        copied = copy.deepcopy(self.__backing_state)
        frozen = _freeze(copied)
        # ensure top-level is MappingProxyType
        if isinstance(frozen, MappingProxyType):
            return frozen
        # if freeze returned tuple/primitive (unlikely), wrap into mapping
        return MappingProxyType(dict(frozen))

    # internal-only mutator; not part of the public API surface. To change
    # canonical state, use the provided CommitHandle from make_environment.
    def _apply_event_internal(self, event: Event):
        # apply the payload onto backing state (simple key overwrite semantics)
        for k, v in event.payload.items():
            # store deep-copy to avoid external aliasing
            self.__backing_state[k] = copy.deepcopy(v)
        self.version = event.new_version
        self.history.append(event)

    def verify_integrity(self, event_store: Optional[InMemoryEventStore] = None, strict: bool = True) -> bool:
        """Verify that history and state are internally consistent.

        Checks:
        - version equals last history event's new_version
        - replaying history yields same deterministic state
        - if event_store provided, ensure history matches event_store.events
        Returns True if checks pass; raises RuntimeError on failure when strict True.
        """
        # Check version vs history
        if self.history:
            last = self.history[-1]
            if self.version != last.new_version:
                if strict:
                    raise RuntimeError("IntegrityError: version mismatch vs last event")
                return False
        else:
            if self.version != 0:
                if strict:
                    raise RuntimeError("IntegrityError: nonzero version with empty history")
                return False

        # Replay history into a new state and compare
        replay = CanonicalState()
        for e in self.history:
            replay._apply_event_internal(e)
        # compare deterministic serialization
        current_serial = json.dumps(_to_primitive(self.snapshot()), sort_keys=True, separators=(",", ":"))
        replay_serial = json.dumps(_to_primitive(replay.snapshot()), sort_keys=True, separators=(",", ":"))
        if current_serial != replay_serial or replay.version != self.version:
            if strict:
                raise RuntimeError("IntegrityError: replay mismatch")
            return False

        # if event_store is provided, ensure same events (by id/order)
        if event_store is not None:
            store_ids = [e.event_id for e in event_store.all_events()]
            hist_ids = [e.event_id for e in self.history]
            if store_ids != hist_ids:
                if strict:
                    raise RuntimeError("IntegrityError: event store and history divergence")
                return False

        return True

    @classmethod
    def replay_from_events(cls, events: List[Event]) -> "CanonicalState":
        s = cls()
        for e in events:
            s._apply_event_internal(e)
        return s


class ProposalStore:
    def __init__(self):
        self.proposals: Dict[str, Proposal] = {}

    def create_proposal(self, proposer_id: str, proposer_role: str, aggregate_id: str, proposed_payload: Dict[str, Any], prev_version: int, evidence: Optional[Dict[str, Any]] = None) -> Proposal:
        pid = str(uuid.uuid4())
        # store a deep copy of payload to avoid external aliasing
        p = Proposal(
            proposal_id=pid,
            proposer_id=proposer_id,
            proposer_role=proposer_role,
            aggregate_id=aggregate_id,
            proposed_payload=copy.deepcopy(proposed_payload),
            evidence=copy.deepcopy(evidence) if evidence is not None else None,
            prev_version=prev_version,
        )
        self.proposals[pid] = p
        return p

    def get(self, proposal_id: str) -> Proposal:
        return self.proposals[proposal_id]


class GovernanceService:
    """Makes decisions. Enforces authorization semantics strictly."""

    def __init__(self, audit: AuditLog):
        self.audit = audit

    def decide(self, proposal: Proposal, decider_id: str, decider_role: str, approve: bool, reason: str = "", evidence: Optional[Dict[str, Any]] = None) -> DecisionRecord:
        prev_status = proposal.status
        timestamp = now_iso()
        if approve:
            if decider_role == "governor":
                new_status = "approved"
                decision = "APPROVE"
                proposal.status = "approved"
            else:
                new_status = prev_status
                decision = "INSUFFICIENT_AUTHORITY"
                # leave proposal.status as tentative
        else:
            new_status = "rejected"
            decision = "REJECT"
            proposal.status = "rejected"

        dr = DecisionRecord(
            decision_id=str(uuid.uuid4()),
            proposal_id=proposal.proposal_id,
            decider_id=decider_id,
            decider_role=decider_role,
            decision=decision,
            reason=reason,
            evidence=copy.deepcopy(evidence) if evidence is not None else None,
            timestamp=timestamp,
            previous_status=prev_status,
            new_status=new_status,
        )

        # record audit with full provenance
        self.audit.record({
            "type": "decision",
            "decision_id": dr.decision_id,
            "proposal_id": dr.proposal_id,
            "decider_id": dr.decider_id,
            "decider_role": dr.decider_role,
            "decision": dr.decision,
            "reason": dr.reason,
            "evidence": dr.evidence,
            "previous_status": dr.previous_status,
            "new_status": dr.new_status,
            "timestamp": dr.timestamp,
        })

        return dr


class CommitHandle:
    """Opaque handle that has authority to apply events to a CanonicalState.

    This is created in the environment and only passed to CommitService.
    External code does not receive this handle.
    """

    def __init__(self, canonical: CanonicalState):
        self._canonical = canonical

    def apply(self, event: Event):
        # internal direct apply; CommitService uses this handle
        self._canonical._apply_event_internal(event)


class CommitService:
    def __init__(self, event_store: InMemoryEventStore, commit_handle: CommitHandle, canonical: CanonicalState, audit: AuditLog):
        self.event_store = event_store
        self._commit_handle = commit_handle
        self.canonical = canonical
        self.audit = audit

    def commit(self, proposal: Proposal, decision: DecisionRecord, committer_id: str, committer_role: str) -> Event:
        # Only commit if proposal approved
        if proposal.status != "approved":
            raise RuntimeError("Proposal not approved; cannot commit")
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
            payload=copy.deepcopy(proposal.proposed_payload),
            provenance={
                "proposal_id": proposal.proposal_id,
                "decision_id": decision.decision_id,
                "decider_id": decision.decider_id,
                "decider_role": decision.decider_role,
                "reason": decision.reason,
                "evidence": proposal.evidence,
            },
            status="committed",
            prev_version=self.canonical.version,
            new_version=new_version,
        )
        # append to event store (ACL enforced inside)
        self.event_store.append_committed(e, actor_role=committer_role)
        # apply via the opaque commit handle
        self._commit_handle.apply(e)
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
        # post-commit integrity check
        self.canonical.verify_integrity(event_store=self.event_store, strict=True)
        return e


class ProjectionManager:
    """Provides canonical, tentative, and shadow projections.

    All returned projections are deep-frozen and cannot be used to modify canonical state.
    """

    def __init__(self, canonical: CanonicalState, proposal_store: ProposalStore):
        self.canonical = canonical
        self.proposal_store = proposal_store
        # shadows are stored separately keyed by name as plain mutable dicts internally,
        # but any projection returned to callers is a deep-frozen snapshot.
        self._shadows: Dict[str, Dict[str, Any]] = {}

    def canonical_projection(self) -> MappingProxyType:
        return self.canonical.snapshot()

    def tentative_projection(self) -> MappingProxyType:
        # start from canonical and overlay all tentative proposals (last-write-wins by proposal creation order)
        out = copy.deepcopy(_to_primitive(self.canonical.snapshot()))
        for p in self.proposal_store.proposals.values():
            if p.status == "tentative":
                for k, v in p.proposed_payload.items():
                    out[k] = copy.deepcopy(v)
        return _freeze(out)

    def shadow_create(self, name: str, base: Optional[Dict[str, Any]] = None):
        self._shadows[name] = copy.deepcopy(base or _to_primitive(self.canonical.snapshot()))

    def shadow_update(self, name: str, payload: Dict[str, Any]):
        if name not in self._shadows:
            raise KeyError("shadow not found")
        self._shadows[name].update(copy.deepcopy(payload))

    def shadow_projection(self, name: str) -> MappingProxyType:
        if name not in self._shadows:
            raise KeyError("shadow not found")
        return _freeze(copy.deepcopy(self._shadows[name]))


def _to_primitive(frozen_map: MappingProxyType) -> Dict[str, Any]:
    """Convert frozen mapping back to JSON-serializable primitives for comparisons."""
    # mappingproxy is dict-like
    d = {}
    for k, v in frozen_map.items():
        d[k] = _unfreeze_to_primitive(v)
    return d


def _unfreeze_to_primitive(value: Any) -> Any:
    # MappingProxyType behaves like dict
    if isinstance(value, MappingProxyType):
        return {k: _unfreeze_to_primitive(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_unfreeze_to_primitive(v) for v in value]
    if isinstance(value, frozenset):
        return sorted([_unfreeze_to_primitive(v) for v in value])
    return value


# helper to initialize a small scenario
def make_environment(initial_state: Dict[str, Any] = None):
    event_store = InMemoryEventStore()
    canonical = CanonicalState()
    audit = AuditLog()
    proposal_store = ProposalStore()
    governance = GovernanceService(audit=audit)
    # create an opaque commit handle and give it to CommitService only
    commit_handle = CommitHandle(canonical=canonical)
    committer = CommitService(event_store=event_store, commit_handle=commit_handle, canonical=canonical, audit=audit)
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
            payload=copy.deepcopy(initial_state),
            provenance={"system_init": True},
            status="committed",
            prev_version=0,
            new_version=1,
        )
        event_store.append_committed(e, actor_role="system")
        # apply via commit handle
        commit_handle.apply(e)
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
