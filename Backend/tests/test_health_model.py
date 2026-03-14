"""
Tests for the Health Model and Multivariate Prediction System
"""

import pytest
from collections import deque
from HealthModel import PumpHealthAnalyzer, HealthMetrics, FailurePrediction


class TestHealthModelBasics:
	"""Test basic health model functionality"""
	
	def test_analyzer_initialization(self):
		"""Test that analyzer initializes correctly"""
		analyzer = PumpHealthAnalyzer(window_size=10)
		assert analyzer.window_size == 10
		assert len(analyzer.temperature_history) == 0
	
	def test_add_reading(self):
		"""Test adding readings to the analyzer"""
		analyzer = PumpHealthAnalyzer()
		analyzer.add_reading(
			temperature=25.0,
			vibration=0.5,
			load_percent=0.0,
			operational_hours=0.0,
			timestamp=0.0
		)
		
		assert len(analyzer.temperature_history) == 1
		assert analyzer.temperature_history[0] == 25.0
	
	def test_window_size_limit(self):
		"""Test that readings respect window size"""
		analyzer = PumpHealthAnalyzer(window_size=5)
		
		for i in range(10):
			analyzer.add_reading(
				temperature=20.0 + i,
				vibration=0.0,
				load_percent=0.0,
				operational_hours=float(i),
				timestamp=float(i)
			)
		
		assert len(analyzer.temperature_history) == 5


class TestNormalization:
	"""Test value normalization"""
	
	def test_normalize_healthy_value(self):
		"""Test normalization of healthy value"""
		analyzer = PumpHealthAnalyzer()
		risk = analyzer._normalize_value(
			value=85.0,  # Normal running temperature
			normal=90.0,
			critical=120.0,
			invert=False
		)
		assert 0.0 <= risk <= 0.1  # Should be very low risk
	
	def test_normalize_critical_value(self):
		"""Test normalization of critical value"""
		analyzer = PumpHealthAnalyzer()
		risk = analyzer._normalize_value(
			value=120.0,  # Critical temperature
			normal=90.0,
			critical=120.0,
			invert=False
		)
		assert abs(risk - 1.0) < 0.01  # Should be ~1.0 risk
	
	def test_normalize_warning_value(self):
		"""Test normalization of warning value"""
		analyzer = PumpHealthAnalyzer()
		risk = analyzer._normalize_value(
			value=105.0,  # Warning temperature
			normal=90.0,
			critical=120.0,
			invert=False
		)
		assert 0.4 < risk < 0.6  # Should be ~0.5


class TestHealthCalculation:
	"""Test health score calculations"""
	
	def test_healthy_pump_health(self):
		"""Test health score for healthy pump"""
		analyzer = PumpHealthAnalyzer()
		health = analyzer.calculate_health(
			temperature=25.0,
			vibration=0.0,
			load_percent=0.0,
			operational_hours=100.0
		)
		
		assert health.overall_health > 0.95
		assert health.trend_status == "healthy"
		assert health.temperature_risk < 0.1
		assert health.vibration_risk < 0.1
	
	def test_degrading_pump_health(self):
		"""Test health score for degrading pump"""
		analyzer = PumpHealthAnalyzer()
		health = analyzer.calculate_health(
			temperature=108.0,
			vibration=4.2,
			load_percent=0.98,
			operational_hours=5000.0
		)
		
		assert 0.4 < health.overall_health < 0.7
		assert health.trend_status == "degrading" or health.trend_status == "at_risk"
	
	def test_critical_pump_health(self):
		"""Test health score for critical pump"""
		analyzer = PumpHealthAnalyzer()
		health = analyzer.calculate_health(
			temperature=118.0,
			vibration=4.8,
			load_percent=1.0,
			operational_hours=9500.0
		)
		
		assert health.overall_health < 0.4
		assert health.trend_status == "critical"
	
	def test_health_metrics_structure(self):
		"""Test that health metrics has all required fields"""
		analyzer = PumpHealthAnalyzer()
		health = analyzer.calculate_health(
			temperature=85.0,
			vibration=2.0,
			load_percent=0.5,
			operational_hours=1000.0
		)
		
		assert hasattr(health, 'temperature_risk')
		assert hasattr(health, 'vibration_risk')
		assert hasattr(health, 'load_risk')
		assert hasattr(health, 'age_risk')
		assert hasattr(health, 'overall_health')
		assert hasattr(health, 'trend_status')
		assert hasattr(health, 'risk_factors')
		
		# Verify risk factors dict
		assert 'temperature' in health.risk_factors
		assert 'vibration' in health.risk_factors
		assert 'load' in health.risk_factors
		assert 'age' in health.risk_factors


class TestLinearRegression:
	"""Test linear regression calculations"""
	
	def test_regression_upward_trend(self):
		"""Test regression detects upward temperature trend"""
		analyzer = PumpHealthAnalyzer()
		
		# Create upward temperature trend
		temps = deque([20.0, 30.0, 40.0, 50.0], maxlen=10)
		times = deque([0.0, 1.0, 2.0, 3.0], maxlen=10)
		
		result = analyzer.calculate_linear_regression(temps, times)
		assert result is not None
		slope, intercept = result
		assert slope > 0  # Positive slope indicates heating
	
	def test_regression_flat_trend(self):
		"""Test regression with flat trend"""
		analyzer = PumpHealthAnalyzer()
		
		temps = deque([50.0, 50.0, 50.0, 50.0], maxlen=10)
		times = deque([0.0, 1.0, 2.0, 3.0], maxlen=10)
		
		result = analyzer.calculate_linear_regression(temps, times)
		assert result is not None
		slope, intercept = result
		assert abs(slope) < 0.1  # Slope should be near zero
	
	def test_regression_insufficient_data(self):
		"""Test regression with insufficient data"""
		analyzer = PumpHealthAnalyzer()
		
		temps = deque([50.0], maxlen=10)
		times = deque([0.0], maxlen=10)
		
		result = analyzer.calculate_linear_regression(temps, times)
		assert result is None


class TestFailurePrediction:
	"""Test failure prediction calculations"""
	
	def test_prediction_healthy_pump(self):
		"""Test prediction for healthy pump"""
		analyzer = PumpHealthAnalyzer()
		prediction = analyzer.predict_failure(
			temperature=25.0,
			vibration=0.0,
			load_percent=0.0,
			operational_hours=100.0
		)
		
		assert isinstance(prediction, FailurePrediction)
		assert prediction.is_at_risk == False
		assert prediction.risk_score < 0.4
		assert "Healthy" in prediction.summary or "green" in prediction.summary.lower()
	
	def test_prediction_at_risk_pump(self):
		"""Test prediction for at-risk pump"""
		analyzer = PumpHealthAnalyzer()
		
		# Add several readings to establish trend with higher risk
		for i in range(5):
			analyzer.add_reading(
				temperature=95.0 + i * 4,  # Gradually heating more
				vibration=3.5 + i * 0.4,  # More vibration
				load_percent=0.85 + i * 0.08,  # Higher load
				operational_hours=float(i),
				timestamp=float(i)
			)
		
		prediction = analyzer.predict_failure(
			temperature=115.0,
			vibration=5.0,
			load_percent=1.0,
			operational_hours=5.0
		)
		
		assert isinstance(prediction, FailurePrediction)
		# High risk scenario should be at_risk or have high risk score
		assert prediction.risk_score > 0.6 or prediction.is_at_risk
		assert prediction.primary_risk_factor in ['temperature', 'vibration', 'load', 'age']
	
	def test_prediction_structure(self):
		"""Test that prediction has all required fields"""
		analyzer = PumpHealthAnalyzer()
		prediction = analyzer.predict_failure(
			temperature=50.0,
			vibration=1.0,
			load_percent=0.5,
			operational_hours=500.0
		)
		
		assert hasattr(prediction, 'is_at_risk')
		assert hasattr(prediction, 'minutes_to_failure')
		assert hasattr(prediction, 'prediction_confidence')
		assert hasattr(prediction, 'primary_risk_factor')
		assert hasattr(prediction, 'risk_score')
		assert hasattr(prediction, 'summary')
		
		# Verify types
		assert isinstance(prediction.is_at_risk, bool)
		assert isinstance(prediction.prediction_confidence, float)
		assert isinstance(prediction.primary_risk_factor, str)
		assert isinstance(prediction.risk_score, float)
		assert isinstance(prediction.summary, str)


class TestMultivariatePrediction:
	"""Test multivariate failure prediction"""
	
	def test_temperature_dominance(self):
		"""Test that high temperature creates highest risk"""
		analyzer = PumpHealthAnalyzer()
		
		# High temp scenario
		health_high_temp = analyzer.calculate_health(
			temperature=115.0,
			vibration=2.0,
			load_percent=0.5,
			operational_hours=1000.0
		)
		
		# Normal scenario
		health_normal = analyzer.calculate_health(
			temperature=85.0,
			vibration=2.0,
			load_percent=0.5,
			operational_hours=1000.0
		)
		
		assert health_high_temp.temperature_risk > health_normal.temperature_risk
		assert health_high_temp.overall_health < health_normal.overall_health
	
	def test_vibration_contribution(self):
		"""Test that vibration contributes to risk"""
		analyzer = PumpHealthAnalyzer()
		
		# High vibration scenario
		health_high_vib = analyzer.calculate_health(
			temperature=85.0,
			vibration=4.5,
			load_percent=0.5,
			operational_hours=1000.0
		)
		
		# Normal scenario
		health_normal = analyzer.calculate_health(
			temperature=85.0,
			vibration=2.0,
			load_percent=0.5,
			operational_hours=1000.0
		)
		
		assert health_high_vib.vibration_risk > health_normal.vibration_risk
		assert health_high_vib.overall_health < health_normal.overall_health
	
	def test_load_contribution(self):
		"""Test that load contributes to risk"""
		analyzer = PumpHealthAnalyzer()
		
		# High load scenario
		health_high_load = analyzer.calculate_health(
			temperature=85.0,
			vibration=2.0,
			load_percent=0.99,
			operational_hours=1000.0
		)
		
		# Normal scenario
		health_normal = analyzer.calculate_health(
			temperature=85.0,
			vibration=2.0,
			load_percent=0.5,
			operational_hours=1000.0
		)
		
		assert health_high_load.load_risk > health_normal.load_risk
		assert health_high_load.overall_health < health_normal.overall_health
	
	def test_age_contribution(self):
		"""Test that operational hours contribute to risk"""
		analyzer = PumpHealthAnalyzer()
		
		# Old pump scenario
		health_old = analyzer.calculate_health(
			temperature=85.0,
			vibration=2.0,
			load_percent=0.5,
			operational_hours=8000.0
		)
		
		# New pump scenario
		health_new = analyzer.calculate_health(
			temperature=85.0,
			vibration=2.0,
			load_percent=0.5,
			operational_hours=500.0
		)
		
		assert health_old.age_risk > health_new.age_risk
		assert health_old.overall_health < health_new.overall_health
	
	def test_combined_degradation(self):
		"""Test that multiple factors combine for overall health"""
		analyzer = PumpHealthAnalyzer()
		
		# Multiple risk factors
		health_degraded = analyzer.calculate_health(
			temperature=110.0,
			vibration=4.0,
			load_percent=0.95,
			operational_hours=7000.0
		)
		
		# Single risk factor each
		health_temp_only = analyzer.calculate_health(
			temperature=110.0,
			vibration=2.0,
			load_percent=0.5,
			operational_hours=500.0
		)
		
		# Multiple risks should create worse health than single risk
		assert health_degraded.overall_health < health_temp_only.overall_health


class TestRealWorldScenarios:
	"""Test realistic pump degradation scenarios"""
	
	def test_gradual_failure_scenario(self):
		"""Test detecting gradual failure over time"""
		analyzer = PumpHealthAnalyzer()
		
		health_scores = []
		
		# Simulate gradual degradation
		for i in range(15):
			health = analyzer.calculate_health(
				temperature=80.0 + i * 2,  # Gradually heating
				vibration=2.0 + i * 0.1,  # Gradually increasing
				load_percent=0.7 + i * 0.02,
				operational_hours=100.0 * (i + 1)
			)
			health_scores.append(health.overall_health)
			analyzer.add_reading(
				temperature=80.0 + i * 2,
				vibration=2.0 + i * 0.1,
				load_percent=0.7 + i * 0.02,
				operational_hours=100.0 * (i + 1),
				timestamp=float(i)
			)
		
		# Health scores should generally decrease
		assert health_scores[-1] < health_scores[0]
	
	def test_sudden_failure_detection(self):
		"""Test detecting sudden failure spike"""
		analyzer = PumpHealthAnalyzer()
		
		# Normal operation
		health_normal = analyzer.calculate_health(
			temperature=85.0,
			vibration=2.5,
			load_percent=0.8,
			operational_hours=500.0
		)
		
		# Sudden spike
		health_spike = analyzer.calculate_health(
			temperature=120.0,
			vibration=5.0,
			load_percent=1.05,
			operational_hours=502.0
		)
		
		# Spike should drop health significantly
		assert health_spike.overall_health < (health_normal.overall_health * 0.5)


if __name__ == '__main__':
	pytest.main([__file__, '-v'])
