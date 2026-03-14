"""
test_pump_analyzer.py
─────────────────────
Test suite for the Hack Island Pump Analyzer.

Four pump scenarios:
  1. CRITICAL  – overheating pump, very high anomaly score (0.93)
  2. HIGH       – elevated risk                            (0.71)
  3. MEDIUM     – watch-and-wait                           (0.52)
  4. LOW        – healthy, no action needed                (0.22)

Usage:
  # Run full test suite (live Gemini skipped unless key is set)
  python test_pump_analyzer.py

  # Run unit tests only (no API calls at all)
  python test_pump_analyzer.py --mock

  # Show a full demo output for all four pumps without hitting Gemini
  python test_pump_analyzer.py --demo
"""

import json
import os
import sys
import time
import unittest
from dataclasses import asdict
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")
from pump_analyzer import (
    PumpAnalyzer,
    PumpAnalysis,
    print_report,
    _derive_severity,
)


# ══════════════════════════════════════════════════════════════════════════════
# Test fixtures
# ══════════════════════════════════════════════════════════════════════════════

PUMP_CRITICAL = {
    "pump-id":              "a3f2c1d4-9b8e-4f7a-b1c2-d3e4f5a6b7c8",
    "temperature":          118.7,   # dangerously high
    "pressure":             9.2,
    "flow-rate":            142.0,   # below nominal (cavitation risk)
    "rpm":                  2950.0,  # near redline
    "operational-hours":    8742.5,  # approaching major service interval
    "requires-maintenance": True,
    "load-percent":         0.97,
    "timestamp":            1715000000,
    "n-state":              0.18,    # severe degradation
    "is-running":           True,
    "anomaly_score":        0.93,
}

PUMP_HIGH = {
    "pump-id":              "b4e3d2c1-0a9f-4e8b-c2d3-e4f5a6b7c8d9",
    "temperature":          97.3,
    "pressure":             8.4,
    "flow-rate":            178.0,
    "rpm":                  2780.0,
    "operational-hours":    5120.0,
    "requires-maintenance": True,
    "load-percent":         0.81,
    "timestamp":            1715000060,
    "n-state":              0.42,
    "is-running":           True,
    "anomaly_score":        0.71,
}

PUMP_MEDIUM = {
    "pump-id":              "c5f4e3d2-1b0a-4f9c-d3e4-f5a6b7c8d9e0",
    "temperature":          82.1,
    "pressure":             7.6,
    "flow-rate":            210.5,
    "rpm":                  2620.0,
    "operational-hours":    2300.0,
    "requires-maintenance": False,
    "load-percent":         0.68,
    "timestamp":            1715000120,
    "n-state":              0.63,
    "is-running":           True,
    "anomaly_score":        0.52,
}

PUMP_LOW = {
    "pump-id":              "d6a5f4e3-2c1b-4a0d-e4f5-a6b7c8d9e0f1",
    "temperature":          74.0,
    "pressure":             7.0,
    "flow-rate":            225.0,
    "rpm":                  2580.0,
    "operational-hours":    900.0,
    "requires-maintenance": False,
    "load-percent":         0.55,
    "timestamp":            1715000180,
    "n-state":              0.88,
    "is-running":           True,
    "anomaly_score":        0.22,
}

ALL_PUMPS = [PUMP_CRITICAL, PUMP_HIGH, PUMP_MEDIUM, PUMP_LOW]


# ══════════════════════════════════════════════════════════════════════════════
# Mock Gemini response
# ══════════════════════════════════════════════════════════════════════════════

def _mock_gemini_response(pump_id: str, severity: str) -> str:
    payload = {
        "engineering_context": (
            f"Pump {pump_id} registers an anomaly score consistent with {severity}-level risk. "
            "Elevated temperature alongside a high load percentage points to thermal runaway, "
            "likely caused by bearing wear or a blocked coolant passage. "
            "The reduced flow rate relative to RPM also suggests impeller erosion or early cavitation."
        ),
        "recommended_action": (
            "1. Immediately reduce pump load to below 70% by adjusting the control valve.\n"
            "2. Inspect coolant line for blockages or leaks at junction J-7.\n"
            "3. Check bearing housing for abnormal vibration using handheld analyser.\n"
            "4. If temperature exceeds 120 \u00b0C, initiate controlled shutdown via isolation valve V-14.\n"
            "5. Log all observations in CMMS and notify the lead engineer on duty."
        ),
        "monitoring_description": (
            f"Pump {pump_id} status: {severity.upper()}. "
            "Temperature and load are beyond safe operational thresholds. "
            "Maintenance dispatch required."
        ),
        "ticket_summary": (
            f"[{severity.upper()}] Pump {pump_id} \u2013 Overheating & elevated anomaly score "
            "\u2013 Dispatch maintenance team immediately."
        ),
        "email_body": (
            f"Dear Hack Island Maintenance Team,\n\n"
            f"This is an automated alert from the AI Pump Monitoring System regarding pump {pump_id}, "
            f"currently flagged at {severity.upper()} severity.\n\n"
            "The pump is operating at dangerously elevated temperature and load. "
            "Because Hack Island has no backup infrastructure, an uncontrolled failure will cause "
            "a complete loss of water and energy supply across the entire facility.\n\n"
            "Required actions:\n"
            "- Reduce pump load and inspect the cooling circuit within the next 15 minutes.\n"
            "- If conditions do not improve, initiate a controlled shutdown and escalate to the "
            "Engineering Lead immediately.\n\n"
            "Please acknowledge this alert within 5 minutes. "
            "If the on-call engineer is unavailable, contact the Site Operations Manager.\n\n"
            "Regards,\nHack Island Autonomous Monitoring System"
        ),
    }
    return json.dumps(payload)


# ══════════════════════════════════════════════════════════════════════════════
# Helper to build a mocked PumpAnalyzer
# ══════════════════════════════════════════════════════════════════════════════

def _build_mocked_analyzer(pump_data: dict) -> PumpAnalyzer:
    severity  = _derive_severity(pump_data["anomaly_score"])
    mock_text = _mock_gemini_response(pump_data["pump-id"], severity)

    mock_response = MagicMock()
    mock_response.text = mock_text

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    with patch("pump_analyzer.genai.configure"), \
         patch("pump_analyzer.genai.GenerativeModel", return_value=mock_model):
        analyzer = PumpAnalyzer(api_key="fake-key-for-test")

    analyzer._model = mock_model
    return analyzer


# ══════════════════════════════════════════════════════════════════════════════
# Unit Tests – pure logic, zero API calls
# ══════════════════════════════════════════════════════════════════════════════

class TestSeverityDerivation(unittest.TestCase):

    def test_critical(self):
        self.assertEqual(_derive_severity(0.93), "critical")
        self.assertEqual(_derive_severity(0.85), "critical")

    def test_high(self):
        self.assertEqual(_derive_severity(0.84), "high")
        self.assertEqual(_derive_severity(0.65), "high")

    def test_medium(self):
        self.assertEqual(_derive_severity(0.64), "medium")
        self.assertEqual(_derive_severity(0.40), "medium")

    def test_low(self):
        self.assertEqual(_derive_severity(0.39), "low")
        self.assertEqual(_derive_severity(0.00), "low")


class TestInputParsing(unittest.TestCase):

    def setUp(self):
        self.analyzer = _build_mocked_analyzer(PUMP_CRITICAL)

    def test_valid_critical_parse(self):
        r = self.analyzer._parse_input(PUMP_CRITICAL)
        self.assertEqual(r.pump_id, PUMP_CRITICAL["pump-id"])
        self.assertAlmostEqual(r.temperature, 118.7)
        self.assertTrue(r.requires_maintenance)
        self.assertAlmostEqual(r.anomaly_score, 0.93)

    def test_valid_low_parse(self):
        r = self.analyzer._parse_input(PUMP_LOW)
        self.assertFalse(r.requires_maintenance)
        self.assertAlmostEqual(r.n_state, 0.88)

    def test_missing_temperature_raises(self):
        bad = {k: v for k, v in PUMP_CRITICAL.items() if k != "temperature"}
        with self.assertRaises(ValueError) as ctx:
            self.analyzer._parse_input(bad)
        self.assertIn("temperature", str(ctx.exception))

    def test_missing_anomaly_score_raises(self):
        bad = {k: v for k, v in PUMP_CRITICAL.items() if k != "anomaly_score"}
        with self.assertRaises(ValueError):
            self.analyzer._parse_input(bad)


class TestResponseParsing(unittest.TestCase):

    def test_clean_json_parsed(self):
        raw    = _mock_gemini_response("test-id", "critical")
        result = PumpAnalyzer._parse_gemini_response(raw)
        for key in ["engineering_context", "recommended_action",
                    "monitoring_description", "ticket_summary", "email_body"]:
            self.assertIn(key, result)

    def test_markdown_fenced_json(self):
        raw    = "```json\n" + _mock_gemini_response("test-id", "high") + "\n```"
        result = PumpAnalyzer._parse_gemini_response(raw)
        self.assertIn("engineering_context", result)

    def test_invalid_json_raises(self):
        with self.assertRaises(ValueError) as ctx:
            PumpAnalyzer._parse_gemini_response("{ this is not json }")
        self.assertIn("invalid JSON", str(ctx.exception))


# ══════════════════════════════════════════════════════════════════════════════
# Integration Tests – full analyze() flow with mocked Gemini
# ══════════════════════════════════════════════════════════════════════════════

class TestAnalyzerMocked(unittest.TestCase):

    def _analyze(self, pump_data):
        return _build_mocked_analyzer(pump_data).analyze(pump_data)

    def test_critical_severity(self):
        result = self._analyze(PUMP_CRITICAL)
        self.assertIsInstance(result, PumpAnalysis)
        self.assertEqual(result.severity, "critical")
        self.assertEqual(result.pump_id, PUMP_CRITICAL["pump-id"])

    def test_high_severity(self):
        self.assertEqual(self._analyze(PUMP_HIGH).severity, "high")

    def test_medium_severity(self):
        self.assertEqual(self._analyze(PUMP_MEDIUM).severity, "medium")

    def test_low_severity(self):
        self.assertEqual(self._analyze(PUMP_LOW).severity, "low")

    def test_all_fields_non_empty_strings(self):
        result = self._analyze(PUMP_CRITICAL)
        for attr in ["engineering_context", "recommended_action",
                     "monitoring_description", "ticket_summary", "email_body"]:
            val = getattr(result, attr)
            self.assertIsInstance(val, str, f"{attr} must be str")
            self.assertGreater(len(val.strip()), 10, f"{attr} must not be empty")

    def test_ticket_contains_severity_label(self):
        result = self._analyze(PUMP_CRITICAL)
        self.assertIn("CRITICAL", result.ticket_summary.upper())

    def test_email_mentions_pump_id(self):
        result = self._analyze(PUMP_CRITICAL)
        self.assertIn(PUMP_CRITICAL["pump-id"], result.email_body)

    def test_serialisable_to_json(self):
        result   = self._analyze(PUMP_CRITICAL)
        d        = asdict(result)
        json_str = json.dumps(d)           # must not raise
        loaded   = json.loads(json_str)
        self.assertEqual(loaded["pump_id"], PUMP_CRITICAL["pump-id"])

    def test_batch_sorted_critical_first(self):
        results = [_build_mocked_analyzer(p).analyze(p) for p in ALL_PUMPS]
        order   = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_ = sorted(results, key=lambda r: order[r.severity])
        self.assertEqual(sorted_[0].severity, "critical")
        self.assertEqual(sorted_[-1].severity, "low")


# ══════════════════════════════════════════════════════════════════════════════
# Live test – real Gemini API (auto-skipped if no key)
# ══════════════════════════════════════════════════════════════════════════════

class TestLiveGemini(unittest.TestCase):

    @unittest.skipUnless(
        os.environ.get("GEMINI_API_KEY"),
        "GEMINI_API_KEY not set – skipping live Gemini test"
    )
    def test_live_critical_pump(self):
        analyzer = PumpAnalyzer()
        result   = analyzer.analyze(PUMP_CRITICAL)

        print("\n\n🔴  LIVE GEMINI RESULT")
        print_report(result)

        self.assertEqual(result.severity, "critical")
        self.assertGreater(len(result.engineering_context), 50)
        self.assertGreater(len(result.email_body), 100)


# ══════════════════════════════════════════════════════════════════════════════
# Demo mode – pretty output for all four pumps, no API call
# ══════════════════════════════════════════════════════════════════════════════

def run_demo():
    print("\n" + "━" * 64)
    print("  HACK ISLAND  –  Pump Monitoring Demo (mocked, no API key needed)")
    print("━" * 64)

    for pump_data in ALL_PUMPS:
        severity = _derive_severity(pump_data["anomaly_score"])
        fields   = json.loads(_mock_gemini_response(pump_data["pump-id"], severity))

        result = PumpAnalysis(
            pump_id                = pump_data["pump-id"],
            severity               = severity,
            engineering_context    = fields["engineering_context"],
            recommended_action     = fields["recommended_action"],
            monitoring_description = fields["monitoring_description"],
            ticket_summary         = fields["ticket_summary"],
            email_body             = fields["email_body"],
        )
        print_report(result)
        time.sleep(0.05)

    print("\n✅  Demo complete. Run with GEMINI_API_KEY set to use the live API.")


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.argv = [a for a in sys.argv if a != "--demo"]
        run_demo()
    else:
        # --mock just signals "no live tests", handled via env var absence
        sys.argv = [a for a in sys.argv if a != "--mock"]
        unittest.main(verbosity=2)
