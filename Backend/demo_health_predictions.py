"""
Demonstration: Compelling Failure Predictions with Multivariate Analysis

This script showcases the professional health model in action, showing:
- Healthy pump vs degrading pump vs critical pump
- Real-time failure predictions with time-to-failure estimates
- Multivariate risk assessment combining temperature, vibration, load, and age
- Professional dashboard output
"""

import time
from Simulation import MyOilFieldSimulation, MyOilPump
from HealthModel import PumpHealthAnalyzer


def print_separator(char="=", length=70):
	"""Print a separator line"""
	print(char * length)


def print_pump_status(pump, pump_number):
	"""Print detailed pump status with professional formatting"""
	print(f"\n📊 PUMP #{pump_number} - Status Report")
	print("-" * 70)
	
	health_metrics = pump.get_health_metrics()
	prediction = pump.predict_failure()
	
	# Health Score with visualization
	health_score = health_metrics.overall_health
	health_bar = "█" * int(health_score * 20) + "░" * (20 - int(health_score * 20))
	
	print(f"  Overall Health: [{health_bar}] {health_score:.2%}")
	print(f"  Status: {health_metrics.trend_status.upper()}")
	print()
	
	# Temperature
	print(f"  🌡️  Temperature: {pump.temperature:.1f}°C")
	print(f"     Risk Level: {health_metrics.temperature_risk:.1%} {'⚠️ WARNING' if health_metrics.temperature_risk > 0.5 else '✓ Normal'}")
	
	# Vibration
	print(f"  📳 Vibration: {pump.vibration:.2f} units")
	print(f"     Risk Level: {health_metrics.vibration_risk:.1%} {'⚠️ WARNING' if health_metrics.vibration_risk > 0.5 else '✓ Normal'}")
	
	# Load
	print(f"  ⚙️  Load: {pump.load_percent:.1%}")
	print(f"     Risk Level: {health_metrics.load_risk:.1%} {'⚠️ WARNING' if health_metrics.load_risk > 0.5 else '✓ Normal'}")
	
	# Operational Hours
	print(f"  ⏱️  Operational Hours: {pump.operational_hours:.1f} hrs")
	print(f"     Age Risk: {health_metrics.age_risk:.1%}")
	
	# Risk Assessment
	print()
	print(f"  📋 Risk Assessment:")
	print(f"     Overall Risk Score: {prediction.risk_score:.1%}")
	print(f"     Primary Risk Factor: {prediction.primary_risk_factor.upper()}")
	print(f"     Prediction Confidence: {prediction.prediction_confidence:.1%}")
	
	# Failure Prediction (THE COMPELLING PART)
	print()
	print(f"  {prediction.summary}")
	if prediction.minutes_to_failure:
		print(f"     💥 Failure projected in {prediction.minutes_to_failure:.1f} minutes")


def demonstrate_health_model():
	"""Demonstrate the health model with three scenarios"""
	
	print_separator("▓")
	print("🏭 OIL FIELD PUMP HEALTH MONITORING SYSTEM")
	print("   Multivariate Analysis with Predictive Failure Detection")
	print_separator("▓")
	
	# Create simulation
	sim = MyOilFieldSimulation()
	
	print("\n📌 SCENARIO 1: HEALTHY PUMP (at rest)")
	print("-" * 70)
	healthy_id = sim.add_oil_pump(
		temperature=22.0,
		vibration=0.0,
		pressure=1.0,
		flow_rate=0.0,
		rpm=0.0,
		operational_hours=100.0,
		requires_maintenance=False,
		load_percent=0.0
	)
	healthy_pump = sim.get_oil_pump(healthy_id)
	print_pump_status(healthy_pump, 1)
	
	print("\n\n📌 SCENARIO 2: NORMAL OPERATION (running well)")
	print("-" * 70)
	normal_id = sim.add_oil_pump(
		temperature=85.0,
		vibration=2.9,
		pressure=205.0,
		flow_rate=11.0,
		rpm=2150.0,
		operational_hours=500.0,
		requires_maintenance=False,
		load_percent=0.95
	)
	normal_pump = sim.get_oil_pump(normal_id)
	print_pump_status(normal_pump, 2)
	
	print("\n\n📌 SCENARIO 3: DEGRADING PUMP (warning signs)")
	print("-" * 70)
	degrading_id = sim.add_oil_pump(
		temperature=108.0,
		vibration=4.0,
		pressure=250.0,
		flow_rate=9.5,
		rpm=1850.0,
		operational_hours=4000.0,
		requires_maintenance=False,
		load_percent=0.98
	)
	degrading_pump = sim.get_oil_pump(degrading_id)
	print_pump_status(degrading_pump, 3)
	
	print("\n\n📌 SCENARIO 4: CRITICAL PUMP (emergency state)")
	print("-" * 70)
	critical_id = sim.add_oil_pump(
		temperature=118.0,
		vibration=4.8,
		pressure=280.0,
		flow_rate=8.0,
		rpm=1500.0,
		operational_hours=8500.0,
		requires_maintenance=True,
		load_percent=1.05
	)
	critical_pump = sim.get_oil_pump(critical_id)
	print_pump_status(critical_pump, 4)


def demonstrate_trend_prediction():
	"""Demonstrate how trends predict failure"""
	
	print_separator("▓")
	print("🔮 TREND ANALYSIS: SIMULATED FAILURE CASCADE")
	print_separator("▓")
	
	sim = MyOilFieldSimulation()
	
	# Create a pump that will degrade over time
	pump_id = sim.add_oil_pump(
		temperature=85.0,
		vibration=2.5,
		load_percent=0.8,
		operational_hours=100.0,
		rpm=2100.0,
		pressure=200.0
	)
	pump = sim.get_oil_pump(pump_id)
	pump.start_pump()
	pump.move_to_error_state()  # Induce an error
	
	print("\nSimulating pump degradation over time...")
	print("(Each tick represents ~1 second of pump operation)\n")
	
	print("TIME │ TEMP │ VIB  │ LOAD │ HEALTH │ STATUS")
	print("-" * 55)
	
	predictions_logged = []
	
	for tick in range(25):
		sim.tick()
		time.sleep(0.05)  # Slight delay for realism
		
		# Get current state
		temp = pump.temperature
		vib = pump.vibration
		load = pump.load_percent
		health = pump.get_estimated_pump_state()
		prediction = pump.predict_failure()
		
		# Determine status emoji
		if prediction.is_at_risk and prediction.minutes_to_failure and prediction.minutes_to_failure < 5:
			status = "🔴 CRITICAL"
		elif prediction.is_at_risk:
			status = "🟠 AT RISK"
		elif health < 0.8:
			status = "🟡 WARN"
		else:
			status = "🟢 OK"
		
		# Print status every 3 ticks or on changes
		if tick % 3 == 0 or prediction.minutes_to_failure is not None:
			print(f" {tick:2} │ {temp:5.1f} │ {vib:4.2f} │ {load:4.2f} │ {health:5.1%} │ {status}")
			
			if prediction.minutes_to_failure and prediction.minutes_to_failure not in [p[1] for p in predictions_logged]:
				predictions_logged.append((tick, prediction.minutes_to_failure))
	
	print()
	print("✅ Simulation showing progressive degradation and failure prediction")


def demonstrate_multivariate_comparison():
	"""Compare single-metric vs multivariate health assessment"""
	
	print_separator("▓")
	print("📊 MULTIVARIATE vs SINGLE-METRIC COMPARISON")
	print_separator("▓")
	
	analyzer = PumpHealthAnalyzer()
	
	scenarios = [
		{
			"name": "High Temperature Only",
			"temp": 115.0,
			"vib": 2.5,
			"load": 0.5,
			"hours": 500.0,
		},
		{
			"name": "High Vibration Only",
			"temp": 85.0,
			"vib": 4.5,
			"load": 0.5,
			"hours": 500.0,
		},
		{
			"name": "Multiple Risk Factors",
			"temp": 110.0,
			"vib": 4.2,
			"load": 0.95,
			"hours": 7000.0,
		},
	]
	
	print("\nComparing health assessment approaches:\n")
	
	for scenario in scenarios:
		health = analyzer.calculate_health(
			temperature=scenario["temp"],
			vibration=scenario["vib"],
			load_percent=scenario["load"],
			operational_hours=scenario["hours"]
		)
		
		print(f"📍 {scenario['name']}")
		print(f"   Conditions: {scenario['temp']:.0f}°C, {scenario['vib']:.1f} vib, {scenario['load']:.0%} load, {scenario['hours']:.0f}h")
		print(f"   Overall Health: {health.overall_health:.1%}")
		print(f"   Risk Breakdown:")
		print(f"     • Temperature: {health.temperature_risk:.1%}")
		print(f"     • Vibration:   {health.vibration_risk:.1%}")
		print(f"     • Load:        {health.load_risk:.1%}")
		print(f"     • Age:         {health.age_risk:.1%}")
		print(f"   Status: {health.trend_status.upper()}")
		print()


def main():
	"""Run all demonstrations"""
	
	print("\n")
	demonstrate_health_model()
	
	print("\n")
	demonstrate_trend_prediction()
	
	print("\n")
	demonstrate_multivariate_comparison()
	
	print_separator("▓")
	print("✅ Demonstration Complete")
	print("   This health model provides:")
	print("   • 0.35 weight on temperature risk")
	print("   • 0.25 weight on vibration risk")
	print("   • 0.20 weight on load risk")
	print("   • 0.20 weight on age/operational hours")
	print("   • Predictive failure timeline estimation")
	print("   • Professional status reporting with emojis")
	print_separator("▓")


if __name__ == "__main__":
	main()
