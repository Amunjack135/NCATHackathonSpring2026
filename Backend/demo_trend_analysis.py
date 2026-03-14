#!/usr/bin/env python
"""
Demonstration script for the trend analysis system
Shows how the system predicts pump failures with linear regression
"""

import csv
import tempfile
from pathlib import Path
from datetime import datetime, timezone
import uuid

from TrendAnalysis import TrendAnalyzer, TrendAnalysisResult


def create_sample_pump_data(tmpdir: Path, pump_id: uuid.UUID, temperature_profile: list, start_time: float = None) -> Path:
	"""
	Create a sample pump CSV file with realistic data
	:param tmpdir: Temporary directory
	:param pump_id: Pump UUID
	:param temperature_profile: List of temperatures to write
	:param start_time: Starting timestamp (optional)
	:return: Path to created CSV file
	"""
	if start_time is None:
		start_time = datetime.now(timezone.utc).timestamp()
	
	csv_path = tmpdir / f'{pump_id}.csv'
	
	with open(csv_path, 'w', newline='') as f:
		writer = csv.writer(f)
		writer.writerow(['Timestamp', 'Temperature', 'Pressure', 'Flow Rate', 'RPM', 
		               'Operational Hours', 'Requires Maintenance', 'Load Percent', 'Is Running'])
		
		for i, temp in enumerate(temperature_profile):
			timestamp = start_time + i * 60  # 1 reading per minute
			pressure = 100 + (temp - 20) * 2  # Pressure correlates with temperature
			flow_rate = 10 + (temp - 20) * 0.2
			rpm = 1000 + (temp - 20) * 10
			operational_hours = i * (1/60)  # Convert minutes to hours
			
			writer.writerow([
				timestamp,
				temp,
				pressure,
				flow_rate,
				rpm,
				operational_hours,
				False,
				0.5 + (temp - 20) * 0.01,
				True
			])
	
	return csv_path


def demo_scenario_1_critical_pump():
	"""
	Scenario 1: Pump heating up rapidly - CRITICAL
	Shows a pump that will fail in approximately 8 minutes
	"""
	print("\n" + "="*80)
	print("SCENARIO 1: RAPIDLY HEATING PUMP - CRITICAL")
	print("="*80)
	
	analyzer = TrendAnalyzer(emergency_threshold=85.0)
	
	with tempfile.TemporaryDirectory() as tmpdir:
		pump_id = uuid.uuid4()
		tmpdir_path = Path(tmpdir)
		
		# Temperature rising at ~1°C per minute (dangerous!)
		# Starting at 50°C, will hit 85°C in about 35 minutes
		temperature_data = [50 + i * 1.0 for i in range(36)]
		
		csv_path = create_sample_pump_data(tmpdir_path, pump_id, temperature_data)
		result = analyzer.analyze_pump(csv_path, pump_id)
		
		print(f"\nPump ID: {pump_id}")
		print(f"Current Temperature: {result.current_temperature:.1f}°C")
		print(f"Heating Rate: {result.temperature_slope:.4f}°C/minute")
		print(f"Emergency Threshold: {result.emergency_threshold:.1f}°C")
		print(f"Confidence (R²): {result.confidence:.2%}")
		print(f"\n⚠️  PREDICTION: {result.get_failure_prediction()}")
		print(f"\nMinutes to Emergency: {result.minutes_to_threshold:.1f} minutes")
		print("\n💡 This is far more compelling than 'temperature too high!'")


def demo_scenario_2_normal_operation():
	"""
	Scenario 2: Pump operating normally - SAFE
	Shows a pump that is stable or cooling
	"""
	print("\n" + "="*80)
	print("SCENARIO 2: NORMAL OPERATION - SAFE")
	print("="*80)
	
	analyzer = TrendAnalyzer(emergency_threshold=85.0)
	
	with tempfile.TemporaryDirectory() as tmpdir:
		pump_id = uuid.uuid4()
		tmpdir_path = Path(tmpdir)
		
		# Temperature stable around 45°C
		temperature_data = [45 + (i % 3 - 1) * 0.5 for i in range(12)]  # Small oscillations
		
		csv_path = create_sample_pump_data(tmpdir_path, pump_id, temperature_data)
		result = analyzer.analyze_pump(csv_path, pump_id)
		
		print(f"\nPump ID: {pump_id}")
		print(f"Current Temperature: {result.current_temperature:.1f}°C")
		print(f"Heating Rate: {result.temperature_slope:.4f}°C/minute")
		print(f"Emergency Threshold: {result.emergency_threshold:.1f}°C")
		print(f"Confidence (R²): {result.confidence:.2%}")
		print(f"\n✅ PREDICTION: {result.get_failure_prediction()}")
		print("\n💡 System recognizes stable operation - no emergency")


def demo_scenario_3_multiple_pumps():
	"""
	Scenario 3: Multiple pumps - Identifies critical ones
	Shows the system's ability to prioritize maintenance on the most critical pumps
	"""
	print("\n" + "="*80)
	print("SCENARIO 3: FLEET MANAGEMENT - MULTI-PUMP ANALYSIS")
	print("="*80)
	
	analyzer = TrendAnalyzer(emergency_threshold=85.0)
	
	with tempfile.TemporaryDirectory() as tmpdir:
		tmpdir_path = Path(tmpdir)
		
		# Create 4 pumps with different scenarios
		pumps = [
			("Normal Operation", [45 + (i % 2) * 0.5 for i in range(12)]),
			("Slow Heating", [40 + i * 0.3 for i in range(12)]),
			("Fast Heating - CRITICAL", [70 + i * 1.2 for i in range(12)]),
			("Cooling Down", [75 - i * 0.8 for i in range(12)]),
		]
		
		pump_ids = {}
		for name, temp_profile in pumps:
			pid = uuid.uuid4()
			pump_ids[name] = pid
			csv_path = create_sample_pump_data(tmpdir_path, pid, temp_profile)
		
		# Analyze all pumps
		results = analyzer.analyze_all_pumps(tmpdir_path)
		
		# Generate comprehensive report
		report = analyzer.generate_report(results)
		print("\n" + report)
		
		# Show critical pumps
		critical = analyzer.get_critical_pumps(results, minutes_warning=20.0)
		print(f"\n🚨 CRITICAL PUMPS (need attention within 20 minutes): {len(critical)}")
		for result in critical:
			print(f"   - Pump {str(result.pump_id)[:8]}...: Failure in ~{result.minutes_to_threshold:.1f} minutes")


def demo_scenario_4_emergency_already_exceeded():
	"""
	Scenario 4: Pump already at emergency threshold
	Shows the system's handling of imminent failure
	"""
	print("\n" + "="*80)
	print("SCENARIO 4: EMERGENCY THRESHOLD EXCEEDED")
	print("="*80)
	
	analyzer = TrendAnalyzer(emergency_threshold=85.0)
	
	with tempfile.TemporaryDirectory() as tmpdir:
		pump_id = uuid.uuid4()
		tmpdir_path = Path(tmpdir)
		
		# Temperature already at/above threshold and rising
		temperature_data = [82 + i * 0.5 for i in range(12)]
		
		csv_path = create_sample_pump_data(tmpdir_path, pump_id, temperature_data)
		result = analyzer.analyze_pump(csv_path, pump_id)
		
		print(f"\nPump ID: {pump_id}")
		print(f"Current Temperature: {result.current_temperature:.1f}°C")
		print(f"Heating Rate: {result.temperature_slope:.4f}°C/minute")
		print(f"Emergency Threshold: {result.emergency_threshold:.1f}°C")
		print(f"\n🔴 CRITICAL: {result.get_failure_prediction()}")
		if result.minutes_to_threshold:
			print(f"\n⚠️  URGENT ACTION REQUIRED - Failure in ~{result.minutes_to_threshold:.2f} minutes!")


def demo_linear_regression_explanation():
	"""
	Show how linear regression gives us predictive power
	"""
	print("\n" + "="*80)
	print("HOW IT WORKS: LINEAR REGRESSION FOR FAILURE PREDICTION")
	print("="*80)
	
	print("""
The trend analysis system performs linear regression over the last 10 temperature 
readings to calculate a trend line. This gives us:

1. SLOPE (°C/minute): How fast the temperature is rising
   - Positive slope = Heating up (concerning)
   - Negative slope = Cooling down (safe)
   - Near zero = Stable operation

2. R² VALUE: Confidence in the trend
   - Close to 1.0 = Strong trend, reliable prediction
   - Close to 0.0 = Weak trend, noisy data

3. TIME TO FAILURE: When will we hit the emergency threshold?
   - Minutes to Failure = (Emergency Threshold - Current Temp) / Slope
   
Example Calculation:
   Current Temp: 78°C
   Slope: 0.5°C/min
   Threshold: 85°C
   
   Time to Failure = (85 - 78) / 0.5 = 14 minutes
   
   System says: "Failure projected in approximately 14 minutes"

This is infinitely more compelling than "Temperature too high!" because:
✓ It gives operators TIME to react
✓ It helps prioritize maintenance across multiple pumps
✓ It's based on actual trend data, not just thresholds
✓ It accounts for the RATE of change, not just absolute values
""")


if __name__ == '__main__':
	print("\n" + "╔" + "="*78 + "╗")
	print("║" + " "*20 + "TREND ANALYSIS DEMONSTRATION" + " "*30 + "║")
	print("║" + " "*15 + "Predictive Maintenance for Oil Field Pumps" + " "*21 + "║")
	print("╚" + "="*78 + "╝")
	
	# Run all demonstration scenarios
	demo_scenario_1_critical_pump()
	demo_scenario_2_normal_operation()
	demo_scenario_3_multiple_pumps()
	demo_scenario_4_emergency_already_exceeded()
	demo_linear_regression_explanation()
	
	print("\n" + "="*80)
	print("DEMONSTRATION COMPLETE")
	print("="*80)
	print("\nThe TrendAnalysis module is ready for integration into:")
	print("• Real-time monitoring dashboards")
	print("• Automated alerting systems")
	print("• Predictive maintenance scheduling")
	print("• Fleet-wide pump health analysis")
	print("\nAll backed by rigorous linear regression and statistical confidence metrics.")
	print("="*80 + "\n")
