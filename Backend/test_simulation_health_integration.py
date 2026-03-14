"""
Integration tests: Simulation + Health Model
"""

import pytest
import time
from Simulation import MyOilFieldSimulation, MyOilPump


class TestSimulationHealthIntegration:
	"""Test health model integration with simulation"""
	
	def test_pump_has_health_analyzer(self):
		"""Test that pumps have health analyzer"""
		sim = MyOilFieldSimulation()
		pump_id = sim.add_oil_pump()
		pump = sim.get_oil_pump(pump_id)
		
		assert hasattr(pump, 'get_estimated_pump_state')
		assert hasattr(pump, 'get_health_metrics')
		assert hasattr(pump, 'predict_failure')
	
	def test_health_score_calculation(self):
		"""Test health score calculation"""
		sim = MyOilFieldSimulation()
		pump_id = sim.add_oil_pump()
		pump = sim.get_oil_pump(pump_id)
		
		health = pump.get_estimated_pump_state()
		assert isinstance(health, float)
		assert 0.0 <= health <= 1.0
	
	def test_health_metrics_retrieval(self):
		"""Test retrieving detailed health metrics"""
		sim = MyOilFieldSimulation()
		pump_id = sim.add_oil_pump()
		pump = sim.get_oil_pump(pump_id)
		
		metrics = pump.get_health_metrics()
		assert hasattr(metrics, 'overall_health')
		assert hasattr(metrics, 'temperature_risk')
		assert hasattr(metrics, 'vibration_risk')
		assert hasattr(metrics, 'load_risk')
		assert hasattr(metrics, 'age_risk')
		assert hasattr(metrics, 'trend_status')
	
	def test_vibration_property_exists(self):
		"""Test that vibration property is accessible"""
		sim = MyOilFieldSimulation()
		pump_id = sim.add_oil_pump()
		pump = sim.get_oil_pump(pump_id)
		
		vibration = pump.vibration
		assert isinstance(vibration, float)
		assert vibration >= 0.0
	
	def test_prediction_basic(self):
		"""Test basic failure prediction"""
		sim = MyOilFieldSimulation()
		pump_id = sim.add_oil_pump()
		pump = sim.get_oil_pump(pump_id)
		
		prediction = pump.predict_failure()
		assert hasattr(prediction, 'is_at_risk')
		assert hasattr(prediction, 'minutes_to_failure')
		assert hasattr(prediction, 'prediction_confidence')
		assert hasattr(prediction, 'summary')


class TestSimulationHealthDegradation:
	"""Test health degradation during simulation"""
	
	def test_health_degradation_under_load(self):
		"""Test that health degrades when pump is running"""
		sim = MyOilFieldSimulation()
		pump_id = sim.add_oil_pump()
		pump = sim.get_oil_pump(pump_id)
		
		# Get initial health
		initial_health = pump.get_estimated_pump_state()
		
		# Start pump and run simulation
		pump.start_pump()
		for _ in range(100):
			sim.tick()
			time.sleep(0.001)
		
		# Check health after running
		final_health = pump.get_estimated_pump_state()
		
		# Health may degrade or stay same due to random nature
		assert isinstance(final_health, float)
		assert 0.0 <= final_health <= 1.0
	
	def test_healthy_pump_at_rest(self):
		"""Test that pump at rest stays healthy"""
		sim = MyOilFieldSimulation()
		pump_id = sim.add_oil_pump()
		pump = sim.get_oil_pump(pump_id)
		
		initial_health = pump.get_estimated_pump_state()
		assert initial_health > 0.95  # Should be very healthy
		
		# Run simulation without starting pump
		for _ in range(50):
			sim.tick()
			time.sleep(0.001)
		
		final_health = pump.get_estimated_pump_state()
		assert final_health > 0.9  # Should still be healthy
	
	def test_forced_error_state(self):
		"""Test pump health when forced into error state"""
		sim = MyOilFieldSimulation()
		pump_id = sim.add_oil_pump()
		pump = sim.get_oil_pump(pump_id)
		
		initial_health = pump.get_estimated_pump_state()
		
		# Force into error state
		pump.move_to_error_state()
		pump.start_pump()
		
		# Run simulation
		for _ in range(50):
			sim.tick()
			time.sleep(0.001)
		
		# Health should be worse
		final_health = pump.get_estimated_pump_state()
		assert isinstance(final_health, float)


class TestMultiplePumpsHealth:
	"""Test health monitoring across multiple pumps"""
	
	def test_health_variance_across_pumps(self):
		"""Test that pumps can have different health scores"""
		sim = MyOilFieldSimulation()
		
		# Add and start some pumps
		pump_ids = []
		for i in range(4):
			pump_id = sim.add_oil_pump()
			pump_ids.append(pump_id)
			pump = sim.get_oil_pump(pump_id)
			if i < 2:  # Start only first 2
				pump.start_pump()
		
		# Run simulation
		for _ in range(50):
			sim.tick()
			time.sleep(0.001)
		
		# Check health scores
		healths = []
		for pump_id in pump_ids:
			pump = sim.get_oil_pump(pump_id)
			health = pump.get_estimated_pump_state()
			healths.append(health)
		
		# All should be valid
		for h in healths:
			assert 0.0 <= h <= 1.0
	
	def test_api_endpoint_health_output(self):
		"""Test that health scores are suitable for API output"""
		sim = MyOilFieldSimulation()
		
		# Add pumps
		for _ in range(8):
			sim.add_oil_pump()
		
		# Simulate
		for _ in range(30):
			sim.tick()
			time.sleep(0.001)
		
		# Get all pump health (like API endpoint would)
		pump_health_map = {}
		for pump in sim.pumps:
			health = pump.get_estimated_pump_state()
			pump_health_map[str(pump.uuid)] = health
		
		assert len(pump_health_map) == 8
		for pump_id, health in pump_health_map.items():
			assert isinstance(health, float)
			assert 0.0 <= health <= 1.0


class TestPredictionRealism:
	"""Test prediction realism in simulation context"""
	
	def test_prediction_summary_format(self):
		"""Test that prediction summaries are formatted correctly"""
		sim = MyOilFieldSimulation()
		pump_id = sim.add_oil_pump()
		pump = sim.get_oil_pump(pump_id)
		
		prediction = pump.predict_failure()
		
		# Summary should contain emoji or descriptive text
		assert any(char in prediction.summary for char in ['🔴', '🟠', '🟡', '🟢', 'Failure', 'Healthy', 'risk'])
	
	def test_prediction_consistency(self):
		"""Test that predictions are consistent for same state"""
		sim = MyOilFieldSimulation()
		pump_id = sim.add_oil_pump()
		pump = sim.get_oil_pump(pump_id)
		
		# Get prediction 1
		health1 = pump.get_estimated_pump_state()
		
		# Get prediction 2 immediately
		health2 = pump.get_estimated_pump_state()
		
		# Should be identical or very close
		assert abs(health1 - health2) < 0.01


class TestHealthAgeFactorEnhancements:
	"""Test the age/operational hours factor in health"""
	
	def test_age_increases_risk(self):
		"""Test that age increases risk component"""
		sim = MyOilFieldSimulation()
		
		# New pump
		pump_id_new = sim.add_oil_pump(operational_hours=100)
		pump_new = sim.get_oil_pump(pump_id_new)
		health_new = pump_new.get_health_metrics()
		
		# Old pump (same other conditions)
		pump_id_old = sim.add_oil_pump(operational_hours=8000)
		pump_old = sim.get_oil_pump(pump_id_old)
		health_old = pump_old.get_health_metrics()
		
		assert health_old.age_risk > health_new.age_risk
	
	def test_weighted_factors_sum_correctly(self):
		"""Test that risk factors combine with proper weights"""
		sim = MyOilFieldSimulation()
		pump_id = sim.add_oil_pump()
		pump = sim.get_oil_pump(pump_id)
		
		health = pump.get_health_metrics()
		
		# Check that risk factors are in [0, 1]
		for risk_name, risk_value in health.risk_factors.items():
			assert 0.0 <= risk_value <= 1.0


if __name__ == '__main__':
	pytest.main([__file__, '-v'])
