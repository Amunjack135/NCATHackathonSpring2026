"""
Health Model Module

Implements multivariate pump health assessment and failure prediction.
Uses weighted normalization across multiple sensor dimensions.
"""

import typing
from dataclasses import dataclass
from collections import deque
import numpy as np


@dataclass
class HealthMetrics:
	"""Container for health assessment metrics"""
	temperature_risk: float
	vibration_risk: float
	load_risk: float
	age_risk: float
	overall_health: float
	risk_factors: dict[str, float]
	trend_status: str


@dataclass
class FailurePrediction:
	"""Container for failure prediction"""
	is_at_risk: bool
	minutes_to_failure: typing.Optional[float]
	prediction_confidence: float
	primary_risk_factor: str
	risk_score: float
	summary: str


class PumpHealthAnalyzer:
	"""Analyzes pump health using multivariate metrics"""
	
	# Thresholds for different metrics
	TEMP_CRITICAL = 120.0  # °C - emergency threshold
	TEMP_WARNING = 105.0   # °C - warning threshold
	TEMP_NORMAL = 90.0     # °C - normal running
	
	VIBRATION_CRITICAL = 5.0
	VIBRATION_WARNING = 3.5
	VIBRATION_NORMAL = 2.95
	
	LOAD_CRITICAL = 1.05
	LOAD_WARNING = 0.98
	LOAD_NORMAL = 0.95
	
	AGE_CRITICAL = 10000.0  # Hours
	AGE_WARNING = 5000.0
	
	# Health weights (must sum to 1.0)
	WEIGHT_TEMPERATURE = 0.402
	WEIGHT_VIBRATION = 0.223
	WEIGHT_LOAD = 0.203
	WEIGHT_AGE = 0.172
	
	def __init__(self, window_size: int = 10):
		"""
		Initialize the health analyzer
		:param window_size: Number of readings to keep for trend analysis
		"""
		self.window_size = window_size
		self.temperature_history: deque = deque(maxlen=window_size)
		self.vibration_history: deque = deque(maxlen=window_size)
		self.load_history: deque = deque(maxlen=window_size)
		self.time_history: deque = deque(maxlen=window_size)
	
	def add_reading(self, temperature: float, vibration: float, load_percent: float, operational_hours: float, timestamp: float) -> None:
		"""
		Add a new pump reading
		:param temperature: Current temperature in °C
		:param vibration: Current vibration level
		:param load_percent: Current load as percentage
		:param operational_hours: Total operational hours
		:param timestamp: Reading timestamp
		"""
		self.temperature_history.append(temperature)
		self.vibration_history.append(vibration)
		self.load_history.append(load_percent)
		self.time_history.append(timestamp)
	
	def _normalize_value(self, value: float, normal: float, critical: float, invert: bool = False) -> float:
		"""
		Normalize a value to 0-1 scale where 1 is critical/bad
		:param value: The value to normalize
		:param normal: The "healthy" baseline value
		:param critical: The critical threshold
		:param invert: If True, lower values are worse
		:return: Normalized risk score (0-1)
		"""
		if invert:
			# For values where lower is worse (e.g., operational efficiency)
			if value >= critical:
				return 1.0
			if value <= normal:
				return 0.0
			return (value - normal) / (critical - normal)
		else:
			# For values where higher is worse (e.g., temperature, vibration)
			if value <= normal:
				return 0.0
			if value >= critical:
				return 1.0
			return (value - normal) / (critical - normal)
	
	def calculate_health(self, temperature: float, vibration: float, load_percent: float, operational_hours: float) -> HealthMetrics:
		"""
		Calculate overall pump health using weighted metrics
		:param temperature: Current temperature in °C
		:param vibration: Current vibration level
		:param load_percent: Current load as percentage (0-1)
		:param operational_hours: Total operational hours
		:return: HealthMetrics with detailed assessment
		"""
		# Normalize each metric to 0-1 risk scale
		temp_risk = self._normalize_value(temperature, self.TEMP_NORMAL, self.TEMP_CRITICAL)
		vibration_risk = self._normalize_value(vibration, self.VIBRATION_NORMAL, self.VIBRATION_CRITICAL)
		load_risk = self._normalize_value(load_percent, self.LOAD_NORMAL, self.LOAD_CRITICAL)
		age_risk = self._normalize_value(operational_hours, self.AGE_WARNING, self.AGE_CRITICAL)
		
		# Calculate weighted health (1 is healthy, 0 is failed)
		overall_risk = (
			temp_risk * self.WEIGHT_TEMPERATURE +
			vibration_risk * self.WEIGHT_VIBRATION +
			load_risk * self.WEIGHT_LOAD +
			age_risk * self.WEIGHT_AGE
		)
		
		# Convert risk to health score (1 is healthy, 0 is failed)
		overall_health = 1.0 - overall_risk
		
		# Determine trend status
		if overall_health > 0.8:
			trend_status = "healthy"
		elif overall_health > 0.6:
			trend_status = "degrading"
		elif overall_health > 0.4:
			trend_status = "at_risk"
		else:
			trend_status = "critical"
		
		risk_factors = {
			'temperature': temp_risk,
			'vibration': vibration_risk,
			'load': load_risk,
			'age': age_risk
		}
		
		return HealthMetrics(
			temperature_risk=temp_risk,
			vibration_risk=vibration_risk,
			load_risk=load_risk,
			age_risk=age_risk,
			overall_health=overall_health,
			risk_factors=risk_factors,
			trend_status=trend_status
		)
	
	def calculate_linear_regression(self, values: deque, times: deque) -> typing.Optional[typing.Tuple[float, float]]:
		"""
		Calculate linear regression slope and intercept
		:param values: The values (e.g., temperatures)
		:param times: The timestamps
		:return: (slope, intercept) or None if insufficient data
		"""
		if len(values) < 2:
			return None
		
		values_array = np.array(list(values), dtype=float)
		times_array = np.array(list(times), dtype=float)
		
		# Normalize times to start at 0 for numerical stability
		times_normalized = times_array - times_array[0]
		
		# Calculate linear regression
		coeffs = np.polyfit(times_normalized, values_array, 1)
		slope = coeffs[0]
		intercept = coeffs[1]
		
		return slope, intercept
	
	def predict_failure(self, temperature: float, vibration: float, load_percent: float, operational_hours: float) -> FailurePrediction:
		"""
		Predict failure based on current metrics and trends
		:param temperature: Current temperature in °C
		:param vibration: Current vibration level
		:param load_percent: Current load as percentage
		:param operational_hours: Total operational hours
		:return: FailurePrediction with time-to-failure estimate
		"""
		self.add_reading(temperature, vibration, load_percent, operational_hours, timestamp=operational_hours * 3600)
		
		# Get current health
		health = self.calculate_health(temperature, vibration, load_percent, operational_hours)
		
		# Calculate trends
		temp_trend = self.calculate_linear_regression(self.temperature_history, self.time_history)
		vib_trend = self.calculate_linear_regression(self.vibration_history, self.time_history)
		load_trend = self.calculate_linear_regression(self.load_history, self.time_history)
		
		# Convert temperature trend to °C/minute
		temp_slope_per_minute = temp_trend[0] / 60 if temp_trend else 0
		vib_slope_per_minute = vib_trend[0] / 60 if vib_trend else 0
		load_slope_per_minute = load_trend[0] / 60 if load_trend else 0
		
		# Calculate minutes to critical thresholds
		minutes_to_temp_critical = None
		if temp_slope_per_minute > 0.01:  # Only if significantly increasing
			temp_margin = self.TEMP_CRITICAL - temperature
			minutes_to_temp_critical = temp_margin / temp_slope_per_minute if temp_slope_per_minute > 0 else None
		
		minutes_to_vib_critical = None
		if vib_slope_per_minute > 0.01:
			vib_margin = self.VIBRATION_CRITICAL - vibration
			minutes_to_vib_critical = vib_margin / vib_slope_per_minute if vib_slope_per_minute > 0 else None
		
		# Combine predictions using multivariate risk scoring
		risk_scores = {
			'temperature': (health.temperature_risk, minutes_to_temp_critical, 0.35),
			'vibration': (health.vibration_risk, minutes_to_vib_critical, 0.25),
			'load': (health.load_risk, None, 0.20),
			'age': (health.age_risk, None, 0.20)
		}
		
		# Find primary risk factor and calculate overall risk
		primary_risk_factor = max(risk_scores.keys(), key=lambda k: risk_scores[k][0])
		overall_risk_score = (
			health.temperature_risk * 0.35 +
			health.vibration_risk * 0.25 +
			health.load_risk * 0.20 +
			health.age_risk * 0.20
		)
		
		# Determine if at risk and project time to failure
		is_at_risk = overall_risk_score > 0.6
		
		minutes_to_failure = None
		confidence = 0.0
		
		if minutes_to_temp_critical and minutes_to_temp_critical < 60:
			minutes_to_failure = minutes_to_temp_critical
			confidence = 0.9
		elif minutes_to_vib_critical and minutes_to_vib_critical < 60:
			minutes_to_failure = minutes_to_vib_critical
			confidence = 0.85
		elif is_at_risk:
			# Estimate based on overall risk trajectory
			minutes_to_failure = max(1, 60 * (1 - overall_risk_score) / overall_risk_score)
			confidence = 0.6
		
		# Generate summary
		if minutes_to_failure and minutes_to_failure < 1440:  # Less than a day
			summary = f"⚠️  Failure projected in approximately {int(minutes_to_failure)} minutes"
		elif overall_risk_score > 0.8:
			summary = "🔴 CRITICAL: Immediate action required"
		elif overall_risk_score > 0.6:
			summary = "🟠 At risk: Close monitoring recommended"
		elif overall_risk_score > 0.4:
			summary = "🟡 Degrading: Schedule maintenance"
		else:
			summary = "🟢 Healthy"
		
		return FailurePrediction(
			is_at_risk=is_at_risk,
			minutes_to_failure=minutes_to_failure,
			prediction_confidence=confidence,
			primary_risk_factor=primary_risk_factor,
			risk_score=overall_risk_score,
			summary=summary
		)


__all__ = ['PumpHealthAnalyzer', 'HealthMetrics', 'FailurePrediction']
