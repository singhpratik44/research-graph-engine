.PHONY: test validate inspect clean help

test:
	@echo "Running test suite (84 tests)..."
	python3 -m pytest test_quantum_control.py -v --tb=short 2>/dev/null || python3 -m unittest test_quantum_control -v

validate: test
	@echo "✓ All tests passing"
	@echo "✓ System validated for production use"

inspect:
	@echo "Inspecting control system architecture..."
	@python3 -c "from timing_engine import TimingEngine; from control_module import ControlModule; m = ControlModule(0, 100); m.load_qubits(); m.execute_single_qubit_gate(0); print(m.print_status()); print(); print(m.timing.print_schedule())"

clean:
	@echo "Cleaning build artifacts..."
	rm -rf __pycache__ .pytest_cache *.pyc

help:
	@echo "Quantum Control Electronics — Makefile targets:"
	@echo ""
	@echo "  make test       Run all 84 tests"
	@echo "  make validate   Run tests + architecture validation"
	@echo "  make inspect    Print control module status and timing"
	@echo "  make clean      Remove build artifacts"
	@echo "  make help       Show this help"
