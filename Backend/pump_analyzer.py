"""
Hack Island - Autonomous AI-Driven Pump Monitoring System
Uses OpenAI API to Detect → Decide → Act → Explain
"""

import json
import os
from dataclasses import dataclass

from openai import OpenAI


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

OPENAI_MODEL = "gpt-4o-mini"  # Fast and affordable. Requires OPENAI_API_KEY environment variable

# Anomaly score thresholds (checked highest-first)
SEVERITY_THRESHOLDS = {
    "critical": 0.85,
    "high":     0.65,
    "medium":   0.40,
    "low":      0.00,
}


# ──────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────

@dataclass
class PumpReading:
    pump_id: str
    temperature: float        # °C
    pressure: float           # Bar
    flow_rate: float          # CFM
    rpm: float                # RPM
    operational_hours: float  # hrs
    requires_maintenance: bool
    load_percent: float       # ratio 0–1
    timestamp: int            # epoch
    n_state: float            # estimated health ratio 0–1
    is_running: bool
    anomaly_score: float      # 0–1, provided alongside sensor data


@dataclass
class PumpAnalysis:
    pump_id: str
    severity: str                    # critical / high / medium / low
    engineering_context: str         # technical root-cause for engineers
    recommended_action: str          # immediate prioritised steps
    monitoring_description: str      # short NOC/dashboard blurb
    ticket_summary: str              # one-liner for ITSM ticket
    email_body: str                  # plain-English email to AD group


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────

def _derive_severity(anomaly_score: float) -> str:
    for level, threshold in SEVERITY_THRESHOLDS.items():
        if anomaly_score >= threshold:
            return level
    return "low"


def _build_prompt(reading: PumpReading, severity: str) -> str:
    return f"""Analyze pump {reading.pump_id}. Temp: {reading.temperature}°C, Pressure: {reading.pressure}Bar, Flow: {reading.flow_rate}CFM, RPM: {reading.rpm}, Health: {reading.n_state:.2f}, Anomaly: {reading.anomaly_score:.2f}, Maintenance: {"YES" if reading.requires_maintenance else "NO"}.

Return ONLY this JSON (no markdown, no extra text):
{{
  "engineering_context": "<1 sentence technical root cause>",
  "recommended_action": "<3-5 steps. Line breaks between steps.>",
  "monitoring_description": "<1 sentence status for dashboard>",
  "ticket_summary": "<1 line. Format: [SEVERITY] Pump ID – issue>",
  "email_body": "<2-3 lines. What happened, why urgent, what to do, who to escalate to.>"
}}"""


# ──────────────────────────────────────────────
# Core analyser class
# ──────────────────────────────────────────────

class PumpAnalyzer:
    """
    Wraps the OpenAI API to produce structured pump analysis.

    Usage:
        analyzer = PumpAnalyzer()
        result   = analyzer.analyze(pump_json_dict)

    The input dict must contain all 12 fields described in the hackathon spec
    plus an "anomaly_score" key (float 0-1).
    
    Requires OPENAI_API_KEY environment variable to be set.
    """

    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key required. Set the OPENAI_API_KEY environment variable."
            )
        self._client = OpenAI(api_key=api_key)

    # ── Public API ───────────────────────────────────────────

    def analyze(self, data: dict) -> PumpAnalysis:
        """
        Analyze a single pump reading.

        Args:
            data: dict matching the hackathon JSON spec + "anomaly_score" key.

        Returns:
            PumpAnalysis dataclass with all output fields populated.
        """
        reading  = self._parse_input(data)
        severity = _derive_severity(reading.anomaly_score)
        prompt   = _build_prompt(reading, severity)
        raw_json = self._call_gemini(prompt)
        fields   = self._parse_gemini_response(raw_json)

        return PumpAnalysis(
            pump_id                = reading.pump_id,
            severity               = severity,
            engineering_context    = fields["engineering_context"],
            recommended_action     = fields["recommended_action"],
            monitoring_description = fields["monitoring_description"],
            ticket_summary         = fields["ticket_summary"],
            email_body             = fields["email_body"],
        )

    def analyze_batch(self, data_list: list) -> list:
        """
        Analyze a list of pump readings and return sorted by severity
        (critical first).
        """
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        results = [self.analyze(d) for d in data_list]
        return sorted(results, key=lambda r: severity_order.get(r.severity, 9))

    # ── Private helpers ──────────────────────────────────────

    @staticmethod
    def _parse_input(data: dict) -> PumpReading:
        required = [
            "pump-id", "temperature", "pressure", "flow-rate",
            "rpm", "operational-hours", "requires-maintenance",
            "load-percent", "timestamp", "n-state", "is-running", "anomaly_score",
        ]
        missing = [k for k in required if k not in data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        return PumpReading(
            pump_id              = data["pump-id"],
            temperature          = float(data["temperature"]),
            pressure             = float(data["pressure"]),
            flow_rate            = float(data["flow-rate"]),
            rpm                  = float(data["rpm"]),
            operational_hours    = float(data["operational-hours"]),
            requires_maintenance = bool(data["requires-maintenance"]),
            load_percent         = float(data["load-percent"]),
            timestamp            = int(data["timestamp"]),
            n_state              = float(data["n-state"]),
            is_running           = bool(data["is-running"]),
            anomaly_score        = float(data["anomaly_score"]),
        )

    def _call_gemini(self, prompt: str) -> str:
        """Call OpenAI API to generate structured response."""
        try:
            response = self._client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}")

    @staticmethod
    def _parse_gemini_response(raw: str) -> dict:
        """Parse JSON with error recovery for incomplete LLM outputs."""
        import re
        
        # Initialize with all required fields
        result = {
            "engineering_context": "[Field unavailable]",
            "recommended_action": "[Field unavailable]",
            "monitoring_description": "[Field unavailable]",
            "ticket_summary": "[Field unavailable]",
            "email_body": "[Field unavailable]",
        }
        
        cleaned = (
            raw.strip()
            .lstrip("```json")
            .lstrip("```")
            .rstrip("```")
            .strip()
        )
        
        # Remove trailing commas before closing braces
        cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
        
        try:
            parsed = json.loads(cleaned)
            # Ensure all required keys exist
            for key in result.keys():
                if key in parsed:
                    result[key] = parsed[key]
            return result
        except json.JSONDecodeError:
            pass
        
        # Fallback: extract fields manually
        for field in result.keys():
            # Try to extract quoted string value
            pattern = f'"{field}"\\s*:\\s*"((?:[^"\\\\]|\\\\.)*)"'
            match = re.search(pattern, cleaned, re.DOTALL)
            if match:
                result[field] = match.group(1).replace('\\"', '"').replace('\\\\n', '\n').replace('\\n', '\n')
        
        return result


# ──────────────────────────────────────────────
# File-based helper
# ──────────────────────────────────────────────

def analyze_from_file(json_path: str) -> list:
    """
    Load a JSON file (single pump dict OR list of pump dicts) and analyze.

    Returns:
        List of PumpAnalysis objects sorted by severity.
    """
    with open(json_path) as f:
        data = json.load(f)

    pumps    = data if isinstance(data, list) else [data]
    analyzer = PumpAnalyzer()
    return analyzer.analyze_batch(pumps)


def analyze_from_json(data: dict[str, float | bool]) -> list:
    """
    Load a JSON string (single pump dict OR list of pump dicts) and analyze.

    Returns:
        List of PumpAnalysis objects sorted by severity.
    """
    pumps    = data if isinstance(data, list) else [data]
    analyzer = PumpAnalyzer()
    return analyzer.analyze_batch(pumps)


# ──────────────────────────────────────────────
# Pretty printer
# ──────────────────────────────────────────────

SEVERITY_ICONS = {
    "critical": "🔴",
    "high":     "🟠",
    "medium":   "🟡",
    "low":      "🟢",
}

def print_report(analysis: PumpAnalysis) -> None:
    """Pretty-print a single PumpAnalysis to stdout."""
    icon = SEVERITY_ICONS.get(analysis.severity, "⚪")
    sep  = "═" * 64

    print(f"\n{sep}")
    print(f"  {icon}  PUMP: {analysis.pump_id}")
    print(f"      SEVERITY: {analysis.severity.upper()}")
    print(sep)

    print("\n📡  MONITORING DESCRIPTION")
    print(f"  {analysis.monitoring_description}")

    print("\n🔧  ENGINEERING CONTEXT")
    print(f"  {analysis.engineering_context}")

    print("\n⚡  RECOMMENDED ACTION")
    for line in analysis.recommended_action.splitlines():
        if line.strip():
            print(f"  {line.strip()}")

    print("\n🎫  TICKET SUMMARY")
    print(f"  {analysis.ticket_summary}")

    print("\n📧  EMAIL BODY")
    print("  " + "─" * 56)
    for line in analysis.email_body.splitlines():
        print(f"  {line}")
    print("  " + "─" * 56)


# ──────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pump_analyzer.py <pump_data.json>")
        sys.exit(1)

    results = analyze_from_file(sys.argv[1])
    for r in results:
        print_report(r)
