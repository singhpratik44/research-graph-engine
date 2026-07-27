# Improvement Roadmap: Closing the Sim-to-Real Gap

This is a phased plan to go from "proof of concept" (current state) to "credible for Google interview" (target state).

**Key principle**: Each improvement reduces one specific sim-to-real gap.

---

## **Phase 1: Validation (HIGH IMPACT, Medium Effort)**
*Proves your assumptions against reality. Takes ~2-4 hours.*

### 1.1 Sensitivity Analysis
**What**: Vary each key assumption ±50%, measure system behavior

**Current state**:
```python
single_qubit_gate_error = 0.001  # 99.9% fidelity
```

**Improved state**:
```python
def sensitivity_analysis():
    for factor in [0.5, 1.0, 1.5, 2.0]:  # Vary ±50%, ±100%
        error_rate = 0.001 * factor
        # Run full system: scheduler + noise model + error correction
        logical_error_rate = run_full_system(error_rate)
        print(f"Physical error 0.1% → {factor}x → Logical {logical_error_rate:.4f}")
        # Measure: fidelity, scheduling latency, correction rounds needed
```

**Expected output**:
```
Physical 0.05% (2x better) → Logical 0.00001% (excellent)
Physical 0.1%  (baseline)  → Logical 0.00030% (good)
Physical 0.2%  (2x worse)  → Logical 0.00120% (marginal)
Physical 0.5%  (5x worse)  → Logical 0.00750% (breaks error correction)
```

**Why it matters**: Shows robustness. "If your hardware is 50% worse than assumed, error correction still works because logical error rate stays below 0.1%."

**Files to update**: `quantum_noise_model.py`, new `test_sensitivity_analysis.py`

---

### 1.2 Compare to Published Google Error Rates
**What**: Cross-reference your assumed rates against Willow paper + recent arXiv

**Current state**: Assume 99.9% single-qubit, 99% two-qubit (generic neutral atom values)

**Improved state**:
```python
# quantum_noise_model.py: Add section "Calibration to Literature"

# Google Willow (Dec 2024): Superconducting
# - Single-qubit: 99.97% ± 0.01%
# - Two-qubit: 99.40% ± 0.10%

# IonQ (published specs): Trapped ions
# - Single-qubit: 99.99%
# - Two-qubit: 98.5%

# Neutral atom (Google Boulder, 2026, estimated)
# - Single-qubit: 99.95% (based on Rydberg laser stability)
# - Two-qubit: 98.5% (harder, based on published neutral atom papers)

# Our model uses: 99.9% (conservative, between IonQ and Boulder estimate)
# Sensitivity: ±0.05% change in single-qubit → see sensitivity_analysis results
```

**Why it matters**: Shows you did homework. "I chose 99.9% because it's between published benchmarks. Here's why, and here's the sensitivity if I'm wrong."

**Action**:
1. Read Google's Willow paper (Nature Dec 2024)
2. Find IonQ published error rates
3. Add table to README comparing your assumed rates to literature
4. Run sensitivity analysis for published rates vs your assumptions

---

## **Phase 2: Real Algorithm Validation (HIGH IMPACT, High Effort)**
*Proves scheduler works on actual quantum algorithms. Takes ~4-6 hours.*

### 2.1 Implement VQE (Variational Quantum Eigensolver)
**What**: Real quantum algorithm, not synthetic sequences

**Why VQE**: 
- Simplest real algorithm (alternates single-qubit rotations + CNOT layers)
- Industry standard for near-term quantum (Google uses this)
- Has measurable fidelity (ansatz quality degrades with noise)

**Implementation**:
```python
# quantum_algorithm_benchmark.py (new file)

class VQEAnsatz:
    def __init__(self, num_qubits=10, num_layers=3):
        self.num_qubits = num_qubits
        self.num_layers = num_layers
        
    def generate_circuit(self, params):
        """Generate VQE ansatz: Ry(θ) gates, then CNOT entanglers, repeat"""
        gates = []
        for layer in range(self.num_layers):
            # Single-qubit rotations
            for q in range(self.num_qubits):
                gates.append({
                    'type': 'Ry',
                    'qubit': q,
                    'angle': params[layer * self.num_qubits + q]
                })
            # Entangling layer
            for q in range(self.num_qubits - 1):
                gates.append({'type': 'CNOT', 'control': q, 'target': q + 1})
        return gates

def benchmark_scheduler_on_vqe():
    """Compare naive vs agentic scheduling on VQE"""
    vqe = VQEAnsatz(num_qubits=20, num_layers=5)
    gates = vqe.generate_circuit(params=[...])
    
    # Naive scheduling
    naive_fidelity = run_with_scheduler(gates, strategy='naive')
    
    # Agentic scheduling (greedy heating)
    agentic_fidelity = run_with_scheduler(gates, strategy='greedy_heating')
    
    improvement = (agentic_fidelity - naive_fidelity) / naive_fidelity * 100
    print(f"VQE benchmark: Agentic improves {improvement:.1f}% over naive")
    return improvement
```

**Expected result**: "Agentic scheduler improves 3–8% on VQE (vs 4–10% on synthetic sequences). Smaller gains because VQE has structured gate patterns that naive scheduling already handles OK."

**Why it matters**: Proof that scheduler helps on *real* algorithms, not just synthetic gates.

---

### 2.2 Run on QAOA (Quantum Approximate Optimization Algorithm)
**What**: More complex algorithm with variable structure

**Why QAOA**: 
- Different structure than VQE (problem-dependent gate placement)
- Has measurement-conditional branching in some variants
- Shows scheduler works on diverse algorithms

**Effort**: Reuse VQE infrastructure, add QAOA ansatz

**Expected result**: "Scheduler performance varies by problem type: MaxCut (4% improvement), graph coloring (6% improvement). Average: 5% ± 1%."

---

## **Phase 3: Latency Realism (HIGH IMPACT, Medium Effort)**
*Model realistic measurement chain. Takes ~2-3 hours.*

### 3.1 Detailed Measurement Latency Model
**Current state**:
```python
measurement_latency_us = 10.0  # Lump-sum assumption
```

**Improved state**:
```python
class RealisticMeasurementChain:
    """Model actual measurement pipeline: detection → digitization → processing → gate"""
    
    def __init__(self):
        # Photon detection (depends on collection efficiency)
        self.photon_detection_time_us = 2.0  # 2μs for fluorescence collection
        
        # Analog-to-digital conversion
        self.adc_time_us = 0.5  # 500ns per qubit (digitization)
        
        # Classical processing (syndrome decoding)
        self.syndrome_decoding_time_us = 5.0  # 5μs for majority vote (3-qubit), 50μs for distance-7
        
        # Gate generation (FPGA output)
        self.gate_generation_time_us = 1.0  # 1μs to send pulse
        
    def total_latency_us(self, num_qubits, code_distance=3):
        """Realistic latency for 1000-qubit system"""
        # Parallel detection (all photons collected together): 2μs
        detection = self.photon_detection_time_us
        
        # Parallel digitization (all ADCs in parallel): 0.5μs
        digitization = self.adc_time_us
        
        # Serial syndrome decoding (limited classical CPU)
        # With 100 modules measuring in parallel, decoder becomes bottleneck
        if code_distance == 3:
            decoding = self.syndrome_decoding_time_us  # 5μs per logical qubit
        else:
            decoding = 50.0  # 50μs for distance-7 surface codes
        
        # Gate generation (routing to right module)
        generation = self.gate_generation_time_us
        
        return detection + digitization + decoding + generation
    
    def can_feedback_per_gate(self, gate_interval_us=0.1):
        """Can we feedback before next gate?"""
        latency = self.total_latency_us(1000, code_distance=3)
        return latency < gate_interval_us * 10  # Need 10x headroom

# Result:
# 3-qubit code: 2 + 0.5 + 5 + 1 = 8.5μs (barely fits, risky)
# Distance-7 code: 2 + 0.5 + 50 + 1 = 53.5μs (doesn't fit; need batch correction)
```

**Why it matters**: Shows you understand real latency. "Per-gate feedback works with 3-qubit code, but distance-7 codes require batch-based correction (measure 10 gates, then correct once)."

---

### 3.2 Revised Closed-Loop Error Correction
**Current state**: Assumes feedback after each gate

**Improved state**: Batch-based correction
```python
def batch_error_correction(gates, batch_size=10):
    """Correct errors in batches, not per-gate"""
    corrected = 0
    for i in range(0, len(gates), batch_size):
        batch = gates[i : i + batch_size]
        
        # Execute batch
        for gate in batch:
            execute_gate(gate)
        
        # After batch: measure all qubits once, correct together
        # Latency: 50μs (acceptable, happens every 10 gates = 1μs of execution)
        syndrome = measure_stabilizers()
        if syndrome_indicates_error(syndrome):
            corrective_action = decode_syndrome(syndrome)
            apply_correction(corrective_action)
        
        corrected += 1
    
    return corrected
```

**Why it matters**: Shows you understand real constraints. "With realistic latencies, feedback is batch-based (measure every 10 gates), not per-gate. Correctness unchanged; latency impact minimal."

---

## **Phase 4: Robustness Testing (MEDIUM IMPACT, Medium Effort)**
*Prove system doesn't break under variations. Takes ~3-4 hours.*

### 4.1 Ablation Studies
**What**: Turn off each component, measure impact

```python
def ablation_study():
    """Measure impact of each architectural component"""
    
    baseline = run_full_system(
        agentic_scheduling=True,
        closed_loop_feedback=True,
        error_correction=True
    )
    
    # Remove agentic scheduling
    naive_only = run_full_system(
        agentic_scheduling=False,  # Back to naive gate ordering
        closed_loop_feedback=True,
        error_correction=True
    )
    
    # Remove feedback
    no_feedback = run_full_system(
        agentic_scheduling=True,
        closed_loop_feedback=False,  # No mid-circuit corrections
        error_correction=True
    )
    
    # Remove error correction
    no_correction = run_full_system(
        agentic_scheduling=True,
        closed_loop_feedback=True,
        error_correction=False  # No repetition code
    )
    
    print(f"Baseline fidelity: {baseline:.4f}")
    print(f"Without agentic: {naive_only:.4f} ({(baseline - naive_only)/baseline * 100:.1f}% loss)")
    print(f"Without feedback: {no_feedback:.4f} ({(baseline - no_feedback)/baseline * 100:.1f}% loss)")
    print(f"Without correction: {no_correction:.4f} ({(baseline - no_correction)/baseline * 100:.1f}% loss)")
```

**Expected output**:
```
Baseline fidelity: 0.9850
Without agentic: 0.9780 (0.7% loss)      ← Scheduler contributes small amount
Without feedback: 0.9620 (2.3% loss)     ← Feedback important
Without correction: 0.8900 (9.7% loss)   ← Error correction critical
```

**Why it matters**: Shows which components actually matter. "Error correction is essential (9.7% impact). Scheduler is nice-to-have (0.7% impact). Feedback is important (2.3% impact)."

---

### 4.2 Stress Tests
**What**: Push system to breaking point

```python
def stress_tests():
    """Find failure modes"""
    
    # What happens with 1000+ gate circuits?
    deep_circuit = generate_vqe(num_qubits=100, num_layers=20)  # 2000+ gates
    fidelity_deep = run_system(deep_circuit)
    print(f"2000-gate circuit: {fidelity_deep:.4f}")  # Expect degradation
    
    # What if error rates are 10x worse?
    high_error = run_system(deep_circuit, error_rate_multiplier=10.0)
    print(f"10x worse errors: {high_error:.4f}")  # Expect failure
    
    # What if entanglement is 50% (not 5%)?
    high_entangle = run_system(deep_circuit, entanglement_fraction=0.5)
    print(f"50% entanglement: {high_entangle:.4f}")  # Expect coordination latency impact
```

**Why it matters**: Shows honest limits. "System works well for <2000 gates and <20% entanglement frequency. Beyond that, need different approach."

---

## **Phase 5: Competitive Comparison (MEDIUM IMPACT, High Effort)**
*Compare to alternatives. Takes ~6-8 hours if implementing RL.*

### 5.1 Implement RL Baseline
**What**: Simple reinforcement learning scheduler

```python
class RLScheduler:
    """Simple policy gradient RL scheduler"""
    
    def __init__(self, state_dim=10, action_dim=100):
        self.policy = SimplePolicy(state_dim, action_dim)
        self.optimizer = Adam(lr=0.01)
        
    def train(self, gates, num_episodes=100):
        """Train RL policy on gate scheduling"""
        for episode in range(num_episodes):
            state = initial_state(gates)
            trajectory = []
            
            for step in range(len(gates)):
                # RL policy selects next gate
                action = self.policy(state)  # Which gate to execute next?
                reward = -heating_cost(action, state)  # Reward is negative heating
                
                trajectory.append((state, action, reward))
                state = update_state(state, action)
            
            # Update policy based on trajectory
            self.optimizer.step(trajectory)
        
        return self.policy

def compare_schedulers():
    """Greedy vs RL"""
    gates = generate_vqe(num_qubits=50, num_layers=5)
    
    # Greedy
    greedy_fidelity = run_with_agentic_scheduler(gates)
    
    # RL (trained)
    rl_scheduler = RLScheduler().train(gates)
    rl_fidelity = run_with_rl_scheduler(gates, rl_scheduler)
    
    print(f"Greedy: {greedy_fidelity:.4f}")
    print(f"RL:     {rl_fidelity:.4f}")
    print(f"Gap: {(rl_fidelity - greedy_fidelity)/greedy_fidelity * 100:.1f}%")
```

**Likely result**: "RL is 2–5% better, but takes 100 episodes to train. Greedy is 'good enough' for real-time."

**Why it matters**: Honest comparison. "My greedy approach is 95–98% as good as RL, but deterministic and real-time. Tradeoff: simplicity vs optimality."

### 5.2 Optimal Scheduling (Branch-and-Bound)
**Effort**: Lower than RL, but still medium
**Likely result**: "Optimal is 5–8% better than greedy on 50-gate problems. Infeasible for 1000+ gates (exponential complexity)."

---

## **Priority Implementation Order**

**Sprint 1 (2-3 hours)**: Do these first
1. ✅ Sensitivity analysis (Phase 1.1)
2. ✅ Compare to published rates (Phase 1.2)
3. ✅ Realistic latency model (Phase 3.1)

**Sprint 2 (4-5 hours)**: Do next
4. ✅ VQE benchmark (Phase 2.1)
5. ✅ Ablation studies (Phase 4.1)

**Sprint 3 (4-6 hours)**: If time permits
6. ✅ QAOA benchmark (Phase 2.2)
7. ✅ RL baseline comparison (Phase 5.1)

**Sprint 4 (2-3 hours)**: Polish
8. ✅ Stress tests (Phase 4.2)
9. ✅ Update documentation with results

---

## **Impact on Credibility**

**Current state** (after reframing):
- "I designed a quantum control architecture"
- Gaps identified, but not tested

**After Phase 1** (2-3 hours):
- "My assumptions are robust: even if error rates are 2x worse, system still works"
- +30% credibility

**After Phase 2** (4-5 hours):
- "Scheduler works on real quantum algorithms (VQE): 5–8% improvement"
- +50% credibility

**After Phase 3** (2-3 hours):
- "Realistic latencies show feedback must be batch-based, not per-gate"
- +40% credibility

**After Phase 4** (3-4 hours):
- "Ablation shows error correction is essential; scheduler is nice-to-have"
- +20% credibility

**After Phase 5** (6-8 hours):
- "Greedy scheduler is 95% as good as RL but deterministic and real-time"
- +40% credibility

**Total**: From "proof of concept" → "credible for research role"

---

## **What NOT to Do**

❌ Implement distance-7 surface codes (too much work, 3-qubit validates principle)
❌ Build actual FPGA controller (out of scope; mention as future work)
❌ Model measurement backaction in detail (low priority)
❌ Implement full quantum circuit simulator (use existing tools like Qiskit)

---

## **Recommended: Do Phases 1–2 (6-8 hours total)**

This closes the biggest gaps with realistic effort. You'll go from "proof of concept" to "credible research-grade work."
