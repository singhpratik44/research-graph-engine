#!/usr/bin/env python3
"""Test suite for hardware_control.py: the injectable control-adapter interface."""

import random
import unittest

import device_graph as dg
import hardware_control as hc


class TestSimulatedControlAdapterConstruction(unittest.TestCase):
    def test_initial_error_rates_seeded_from_device(self):
        device = dg.linear_chain(3, qubit_error_rate=0.05, edge_error_rate=0.1)
        adapter = hc.SimulatedControlAdapter(device, rng=random.Random(1))
        reading = adapter.read_telemetry(0)
        self.assertEqual(reading.error_rate, 0.05)


class TestCalibrate(unittest.TestCase):
    def test_returns_report_for_every_qubit_and_edge(self):
        device = dg.linear_chain(3, qubit_error_rate=0.01, edge_error_rate=0.02)
        adapter = hc.SimulatedControlAdapter(device, rng=random.Random(1))
        report = adapter.calibrate(device)
        self.assertEqual(set(report.qubit_error_rate), {0, 1, 2})
        self.assertEqual(set(report.edge_error_rate), {(0, 1), (1, 2)})

    def test_error_rates_stay_within_unit_interval(self):
        device = dg.linear_chain(3, qubit_error_rate=0.9, edge_error_rate=0.9)
        adapter = hc.SimulatedControlAdapter(device, rng=random.Random(1), drift_scale=0.5)
        for _ in range(50):
            report = adapter.calibrate(device)
            for rate in list(report.qubit_error_rate.values()) + list(report.edge_error_rate.values()):
                self.assertGreaterEqual(rate, 0.0)
                self.assertLessEqual(rate, 1.0)

    def test_same_seed_is_reproducible(self):
        device = dg.linear_chain(3, qubit_error_rate=0.05, edge_error_rate=0.1)
        adapter_a = hc.SimulatedControlAdapter(device, rng=random.Random(7))
        adapter_b = hc.SimulatedControlAdapter(device, rng=random.Random(7))
        report_a = adapter_a.calibrate(device)
        report_b = adapter_b.calibrate(device)
        self.assertEqual(report_a.qubit_error_rate, report_b.qubit_error_rate)
        self.assertEqual(report_a.edge_error_rate, report_b.edge_error_rate)

    def test_calibrate_updates_subsequent_telemetry(self):
        device = dg.linear_chain(3, qubit_error_rate=0.05, edge_error_rate=0.1)
        adapter = hc.SimulatedControlAdapter(device, rng=random.Random(2))
        report = adapter.calibrate(device)
        reading = adapter.read_telemetry(0)
        self.assertEqual(reading.error_rate, report.qubit_error_rate[0])

    def test_mismatched_device_raises(self):
        device = dg.linear_chain(3)
        other_device = dg.linear_chain(4)
        adapter = hc.SimulatedControlAdapter(device, rng=random.Random(1))
        with self.assertRaises(dg.InvalidDeviceGraphError):
            adapter.calibrate(other_device)


class TestApplyPulse(unittest.TestCase):
    def test_zero_error_rate_always_succeeds(self):
        device = dg.linear_chain(2, qubit_error_rate=0.0)
        adapter = hc.SimulatedControlAdapter(device, rng=random.Random(1))
        pulse = hc.PulseSpec(frequency_ghz=5.0, amplitude=0.5, duration_ns=20.0)
        for _ in range(20):
            result = adapter.apply_pulse(0, pulse)
            self.assertTrue(result.success)

    def test_certain_error_rate_always_fails(self):
        device = dg.linear_chain(2, qubit_error_rate=1.0)
        adapter = hc.SimulatedControlAdapter(device, rng=random.Random(1))
        pulse = hc.PulseSpec(frequency_ghz=5.0, amplitude=0.5, duration_ns=20.0)
        for _ in range(20):
            result = adapter.apply_pulse(0, pulse)
            self.assertFalse(result.success)

    def test_reports_measured_error_rate(self):
        device = dg.linear_chain(2, qubit_error_rate=0.3)
        adapter = hc.SimulatedControlAdapter(device, rng=random.Random(1))
        pulse = hc.PulseSpec(frequency_ghz=5.0, amplitude=0.5, duration_ns=20.0)
        result = adapter.apply_pulse(0, pulse)
        self.assertEqual(result.measured_error_rate, 0.3)

    def test_unknown_qubit_raises(self):
        device = dg.linear_chain(2)
        adapter = hc.SimulatedControlAdapter(device, rng=random.Random(1))
        pulse = hc.PulseSpec(frequency_ghz=5.0, amplitude=0.5, duration_ns=20.0)
        with self.assertRaises(dg.InvalidDeviceGraphError):
            adapter.apply_pulse(99, pulse)


class TestReadTelemetry(unittest.TestCase):
    def test_unknown_qubit_raises(self):
        device = dg.linear_chain(2)
        adapter = hc.SimulatedControlAdapter(device, rng=random.Random(1))
        with self.assertRaises(dg.InvalidDeviceGraphError):
            adapter.read_telemetry(99)

    def test_distinct_qubits_get_distinct_frequencies(self):
        device = dg.linear_chain(3)
        adapter = hc.SimulatedControlAdapter(device, rng=random.Random(1))
        frequencies = {adapter.read_telemetry(q).frequency_ghz for q in device.qubits}
        self.assertEqual(len(frequencies), 3)


if __name__ == "__main__":
    unittest.main()
