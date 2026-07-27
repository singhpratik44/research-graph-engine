#!/usr/bin/env python3
"""
Dashboard Scaffold: Observability & Operator Control Surface

Provides:
- Real-time loop state visualization
- Latency trend lines
- Confidence and recovery pressure metrics
- Graph layer summaries
- PIV stage progress
- Bounded autonomy settings
- Module ownership matrix

FastAPI server exposing read models from all controller services.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from enum import Enum
import json
from datetime import datetime, timezone

from quantum_schema import (
    QuantumGraph, RuntimeEvent, GraphMetrics, FreshnessLevel,
    LoopPhaseMetrics, ConfidenceLevel
)
from quantum_constraints import ActionEnvelope


# ============================================================================
# DASHBOARD DATA MODELS
# ============================================================================

@dataclass
class LoopStateSnapshot:
    """Real-time state of the agentic feedback loop."""
    timestamp: str
    iteration_count: int
    current_phase: str  # "sense", "estimate", "constrain", "act", "validate", "learn"
    phase_duration_ms: float
    phase_confidence: float  # 0.0 - 1.0
    total_loop_time_ms: float
    phases: List[LoopPhaseMetrics] = field(default_factory=list)
    last_action_id: Optional[str] = None
    last_action_confidence: Optional[float] = None
    anomalies: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "iteration_count": self.iteration_count,
            "current_phase": self.current_phase,
            "phase_duration_ms": self.phase_duration_ms,
            "phase_confidence": self.phase_confidence,
            "total_loop_time_ms": self.total_loop_time_ms,
            "phases": [p.to_dict() for p in self.phases],
            "last_action_id": self.last_action_id,
            "last_action_confidence": self.last_action_confidence,
            "anomalies": self.anomalies
        }


@dataclass
class GraphLayerSummary:
    """Summary of one graph layer."""
    layer_name: str
    node_count: int
    edge_count: int
    node_types: Dict[str, int]  # type -> count
    edge_types: Dict[str, int]  # type -> count
    freshness: FreshnessLevel
    constraint_violations: int
    confidence: float

    def to_dict(self):
        return {
            "layer_name": self.layer_name,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "node_types": self.node_types,
            "edge_types": self.edge_types,
            "freshness": self.freshness.value,
            "constraint_violations": self.constraint_violations,
            "confidence": self.confidence
        }


@dataclass
class PIVStageStatus:
    """Progress on one PIV stage."""
    stage_name: str  # "prototype", "integrate", "validate", "scale"
    status: str  # "pending", "in_progress", "completed", "blocked"
    completion_percent: float  # 0.0 - 100.0
    completed_tasks: int
    total_tasks: int
    blocker_description: Optional[str] = None
    evidence_count: int = 0

    def to_dict(self):
        return {
            "stage_name": self.stage_name,
            "status": self.status,
            "completion_percent": self.completion_percent,
            "completed_tasks": self.completed_tasks,
            "total_tasks": self.total_tasks,
            "blocker_description": self.blocker_description,
            "evidence_count": self.evidence_count
        }


@dataclass
class AutonomySettings:
    """Bounded autonomy configuration."""
    max_retry_budget: int
    escalation_threshold: float  # confidence floor for autonomous action
    approval_required_for_critical: bool
    recovery_policy: str  # "conservative", "balanced", "aggressive"
    max_concurrent_actions: int
    human_override_enabled: bool

    def to_dict(self):
        return asdict(self)


@dataclass
class ServiceStatus:
    """One service health snapshot."""
    service_name: str
    healthy: bool
    latency_ms: float
    error_count: int
    request_count: int
    uptime_seconds: float
    last_error: Optional[str] = None

    def to_dict(self):
        return {
            "service_name": self.service_name,
            "healthy": self.healthy,
            "latency_ms": self.latency_ms,
            "error_count": self.error_count,
            "request_count": self.request_count,
            "uptime_seconds": self.uptime_seconds,
            "last_error": self.last_error
        }


@dataclass
class ModuleOwnershipMatrix:
    """Service implementation ownership and order."""
    modules: List[Dict[str, Any]] = field(default_factory=list)

    def add_module(
        self,
        name: str,
        responsibility: str,
        phase: str,
        status: str,  # "planned", "in_progress", "complete"
        owner: Optional[str] = None,
        depends_on: List[str] = None
    ):
        """Add module to ownership matrix."""
        self.modules.append({
            "name": name,
            "responsibility": responsibility,
            "phase": phase,
            "status": status,
            "owner": owner,
            "depends_on": depends_on or []
        })

    def to_dict(self):
        return {"modules": self.modules}


@dataclass
class ControllerOverview:
    """Complete controller dashboard snapshot."""
    timestamp: str
    loop_state: Optional[LoopStateSnapshot] = None
    graph_layers: List[GraphLayerSummary] = field(default_factory=list)
    piv_stages: List[PIVStageStatus] = field(default_factory=list)
    autonomy_settings: Optional[AutonomySettings] = None
    services: List[ServiceStatus] = field(default_factory=list)
    module_matrix: Optional[ModuleOwnershipMatrix] = None
    kpis: Dict[str, float] = field(default_factory=dict)

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "loop_state": self.loop_state.to_dict() if self.loop_state else None,
            "graph_layers": [g.to_dict() for g in self.graph_layers],
            "piv_stages": [p.to_dict() for p in self.piv_stages],
            "autonomy_settings": self.autonomy_settings.to_dict() if self.autonomy_settings else None,
            "services": [s.to_dict() for s in self.services],
            "module_matrix": self.module_matrix.to_dict() if self.module_matrix else None,
            "kpis": self.kpis
        }


# ============================================================================
# DASHBOARD BACKEND
# ============================================================================

class DashboardBackend:
    """In-memory dashboard state manager."""

    def __init__(self):
        self.loop_state: Optional[LoopStateSnapshot] = None
        self.graph_layers: Dict[str, GraphLayerSummary] = {}
        self.piv_stages: Dict[str, PIVStageStatus] = {}
        self.autonomy_settings: Optional[AutonomySettings] = None
        self.services: Dict[str, ServiceStatus] = {}
        self.module_matrix: Optional[ModuleOwnershipMatrix] = None
        self.event_history: List[RuntimeEvent] = []
        self.max_event_history = 1000

    def update_loop_state(self, state: LoopStateSnapshot):
        """Update real-time loop state."""
        self.loop_state = state

    def update_graph_layer(self, layer: GraphLayerSummary):
        """Update one graph layer summary."""
        self.graph_layers[layer.layer_name] = layer

    def update_piv_stage(self, stage: PIVStageStatus):
        """Update one PIV stage status."""
        self.piv_stages[stage.stage_name] = stage

    def update_service_status(self, status: ServiceStatus):
        """Update one service health status."""
        self.services[status.service_name] = status

    def set_autonomy_settings(self, settings: AutonomySettings):
        """Update bounded autonomy settings."""
        self.autonomy_settings = settings

    def set_module_matrix(self, matrix: ModuleOwnershipMatrix):
        """Set service implementation matrix."""
        self.module_matrix = matrix

    def record_event(self, event: RuntimeEvent):
        """Record runtime event for history."""
        self.event_history.append(event)
        if len(self.event_history) > self.max_event_history:
            self.event_history.pop(0)

    def get_overview(self) -> ControllerOverview:
        """Get complete dashboard snapshot."""
        overview = ControllerOverview(
            timestamp=datetime.now(timezone.utc).isoformat(),
            loop_state=self.loop_state,
            graph_layers=list(self.graph_layers.values()),
            piv_stages=list(self.piv_stages.values()),
            autonomy_settings=self.autonomy_settings,
            services=list(self.services.values()),
            module_matrix=self.module_matrix
        )

        # Compute KPIs
        if self.loop_state:
            overview.kpis["avg_loop_time_ms"] = self.loop_state.total_loop_time_ms
            overview.kpis["loop_confidence"] = self.loop_state.phase_confidence

        if self.piv_stages:
            avg_completion = sum(s.completion_percent for s in self.piv_stages.values()) / len(self.piv_stages)
            overview.kpis["piv_overall_completion"] = avg_completion

        if self.services:
            healthy_count = sum(1 for s in self.services.values() if s.healthy)
            overview.kpis["services_healthy_percent"] = (healthy_count / len(self.services)) * 100

        # Anomaly count
        anomaly_count = sum(len(s.anomalies) for s in self.graph_layers.values() if hasattr(s, 'anomalies'))
        overview.kpis["anomaly_count"] = anomaly_count

        return overview

    def get_event_history(self, limit: int = 100) -> List[RuntimeEvent]:
        """Get recent event history."""
        return self.event_history[-limit:]

    def get_latency_trends(self, window_size: int = 50) -> Dict[str, List[float]]:
        """Get latency trend lines from recent events."""
        trends: Dict[str, List[float]] = {}

        for event in self.event_history[-window_size:]:
            if event.phase not in trends:
                trends[event.phase] = []
            # Extract latency from metadata if available
            if "latency_ms" in event.metadata:
                trends[event.phase].append(event.metadata["latency_ms"])

        return trends


# ============================================================================
# FASTAPI INTEGRATION SKELETON
# ============================================================================

def create_dashboard_routes():
    """Factory for FastAPI dashboard routes (skeleton)."""
    try:
        from fastapi import FastAPI
        app = FastAPI(title="Quantum-Classical OS Controller Dashboard")
        backend = DashboardBackend()

        @app.get("/api/overview")
        def get_overview():
            """Get complete controller overview."""
            return backend.get_overview().to_dict()

        @app.get("/api/loop-state")
        def get_loop_state():
            """Get real-time feedback loop state."""
            if backend.loop_state:
                return backend.loop_state.to_dict()
            return None

        @app.get("/api/graph-layers")
        def get_graph_layers():
            """Get all graph layer summaries."""
            return {name: layer.to_dict() for name, layer in backend.graph_layers.items()}

        @app.get("/api/piv-progress")
        def get_piv_progress():
            """Get PIV stage progress."""
            return {name: stage.to_dict() for name, stage in backend.piv_stages.items()}

        @app.get("/api/services")
        def get_services():
            """Get service health statuses."""
            return {name: status.to_dict() for name, status in backend.services.items()}

        @app.get("/api/events")
        def get_events(limit: int = 100):
            """Get event history."""
            return [e.to_dict() for e in backend.get_event_history(limit)]

        @app.get("/api/latency-trends")
        def get_latency_trends():
            """Get latency trend lines."""
            return backend.get_latency_trends()

        @app.get("/api/autonomy-settings")
        def get_autonomy_settings():
            """Get bounded autonomy configuration."""
            if backend.autonomy_settings:
                return backend.autonomy_settings.to_dict()
            return None

        @app.get("/api/module-matrix")
        def get_module_matrix():
            """Get module ownership matrix."""
            if backend.module_matrix:
                return backend.module_matrix.to_dict()
            return None

        return app, backend

    except ImportError:
        # FastAPI not available; provide stubs
        return None, DashboardBackend()


# Singleton backend instance
_dashboard_backend: Optional[DashboardBackend] = None


def get_dashboard_backend() -> DashboardBackend:
    """Get or create singleton dashboard backend."""
    global _dashboard_backend
    if _dashboard_backend is None:
        _dashboard_backend = DashboardBackend()
    return _dashboard_backend
