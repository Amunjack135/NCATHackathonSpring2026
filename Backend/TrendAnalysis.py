import csv
import typing
import uuid
from pathlib import Path
from dataclasses import dataclass
import numpy as np
from scipy import stats


@dataclass
class TemperatureReading:
	"""Represents a single temperature reading"""
	timestamp: float
	temperature: float
	is_running: bool


@dataclass
class TrendAnalysisResult:
	"""Result of trend analysis"""
	pump_id: uuid.UUID
	current_temperature: float
	temperature_slope: float  # °C per minute
	minutes_to_threshold: typing.Optional[float]  # None if slope is negative or zero
	confidence: float  # R² value (0 to 1)
	readings_count: int
	emergency_threshold: float
	
	def get_failure_prediction(self) -> str:
		"""
		Returns a human-readable failure prediction
		"""
		if self.minutes_to_threshold is None:
			return "Temperature cooling down or stable"
		
		if self.minutes_to_threshold < 0:
			return f"Already exceeded threshold by {abs(self.minutes_to_threshold):.1f} minutes"
		
		if self.minutes_to_threshold < 1:
			return "CRITICAL: Failure imminent (< 1 minute)"
		
		if self.minutes_to_threshold < 5:
			return f"⚠️  WARNING: Failure in approximately {self.minutes_to_threshold:.1f} minutes"
		
		return f"Failure projected in approximately {self.minutes_to_threshold:.1f} minutes"


class TrendAnalyzer:
	"""Analyzes temperature trends and predicts pump failures"""
	
	def __init__(self, emergency_threshold: float = 85.0, analysis_readings: int = 10):
		"""
		Initialize the trend analyzer
		:param emergency_threshold: Temperature threshold that triggers emergency (°C)
		:param analysis_readings: Number of recent readings to analyze
		"""
		self.emergency_threshold = emergency_threshold
		self.analysis_readings = analysis_readings
	
	def read_pump_csv(self, csv_path: Path) -> typing.List[TemperatureReading]:
		"""
		Read temperature data from a pump CSV file
		:param csv_path: Path to the pump CSV file
		:return: List of temperature readings
		"""
		readings: typing.List[TemperatureReading] = []
		
		try:
			with open(csv_path, 'r') as f:
				reader = csv.DictReader(f)
				for row in reader:
					try:
						readings.append(TemperatureReading(
							timestamp=float(row['Timestamp']),
							temperature=float(row['Temperature']),
							is_running=row['Is Running'].lower() == 'true'
						))
					except (ValueError, KeyError) as e:
						# Skip invalid rows
						continue
		except FileNotFoundError:
			return []
		
		return readings
	
	def analyze_pump(self, csv_path: Path, pump_id: typing.Optional[uuid.UUID] = None) -> typing.Optional[TrendAnalysisResult]:
		"""
		Analyze a single pump's temperature trend
		:param csv_path: Path to the pump CSV file
		:param pump_id: The pump ID (used for result identification)
		:return: TrendAnalysisResult or None if insufficient data
		"""
		readings = self.read_pump_csv(csv_path)
		
		if len(readings) < 2:
			return None
		
		# Get the last N readings
		recent_readings = readings[-self.analysis_readings:]
		
		# If pump ID not provided, try to extract from filename
		if pump_id is None:
			try:
				pump_id = uuid.UUID(csv_path.stem)
			except (ValueError, AttributeError):
				pump_id = uuid.uuid4()
		
		# Extract timestamps and temperatures
		timestamps = np.array([r.timestamp for r in recent_readings])
		temperatures = np.array([r.temperature for r in recent_readings])
		
		# Convert timestamps to minutes from the first reading
		time_minutes = (timestamps - timestamps[0]) / 60.0
		
		# Perform linear regression
		slope, intercept, r_value, p_value, std_err = stats.linregress(time_minutes, temperatures)
		
		# Current temperature is the latest reading
		current_temperature = temperatures[-1]
		
		# Calculate minutes to threshold
		minutes_to_threshold = None
		if slope > 0.001:  # Only calculate if temperature is actually rising
			minutes_to_threshold = (self.emergency_threshold - current_temperature) / slope
		
		return TrendAnalysisResult(
			pump_id=pump_id,
			current_temperature=current_temperature,
			temperature_slope=slope,  # °C per minute
			minutes_to_threshold=minutes_to_threshold,
			confidence=r_value ** 2,  # R² value
			readings_count=len(recent_readings),
			emergency_threshold=self.emergency_threshold
		)
	
	def analyze_all_pumps(self, data_directory: Path) -> typing.Dict[uuid.UUID, TrendAnalysisResult]:
		"""
		Analyze all pump CSV files in a directory
		:param data_directory: Directory containing pump CSV files
		:return: Dictionary mapping pump IDs to analysis results
		"""
		results: typing.Dict[uuid.UUID, TrendAnalysisResult] = {}
		
		if not data_directory.exists():
			return results
		
		# Find all CSV files
		csv_files = list(data_directory.glob('*.csv'))
		
		for csv_file in csv_files:
			try:
				pump_id = uuid.UUID(csv_file.stem)
				result = self.analyze_pump(csv_file, pump_id)
				if result is not None:
					results[pump_id] = result
			except (ValueError, TypeError):
				# Skip files that don't have valid UUID names
				continue
		
		return results
	
	def get_critical_pumps(self, results: typing.Dict[uuid.UUID, TrendAnalysisResult], 
	                        minutes_warning: float = 15.0) -> typing.List[TrendAnalysisResult]:
		"""
		Get pumps that are projected to fail within the warning time
		:param results: Dictionary of analysis results
		:param minutes_warning: Minutes until failure to consider critical
		:return: Sorted list of critical pumps (closest to failure first)
		"""
		critical = []
		
		for result in results.values():
			if result.minutes_to_threshold is not None and result.minutes_to_threshold > 0:
				if result.minutes_to_threshold <= minutes_warning:
					critical.append(result)
		
		# Sort by minutes_to_threshold (ascending)
		critical.sort(key=lambda r: r.minutes_to_threshold if r.minutes_to_threshold else float('inf'))
		
		return critical
	
	def generate_report(self, results: typing.Dict[uuid.UUID, TrendAnalysisResult]) -> str:
		"""
		Generate a human-readable report of all pump analyses
		:param results: Dictionary of analysis results
		:return: Formatted report string
		"""
		if not results:
			return "No pump data available for analysis"
		
		critical_pumps = self.get_critical_pumps(results)
		
		report_lines = [
			"=== PUMP TREND ANALYSIS REPORT ===",
			f"Total Pumps Analyzed: {len(results)}",
			f"Critical Pumps (failing within 15 min): {len(critical_pumps)}",
			""
		]
		
		if critical_pumps:
			report_lines.append("CRITICAL PUMPS (PRIORITY ORDER):")
			report_lines.append("-" * 80)
			for result in critical_pumps:
				report_lines.append(f"Pump {str(result.pump_id)[:8]}...")
				report_lines.append(f"  Current Temp: {result.current_temperature:.1f}°C")
				report_lines.append(f"  Heating Rate: {result.temperature_slope:.3f}°C/min")
				report_lines.append(f"  {result.get_failure_prediction()}")
				report_lines.append(f"  Confidence: {result.confidence * 100:.1f}%")
				report_lines.append(f"  Based on {result.readings_count} readings")
				report_lines.append("")
		
		# Summary of all pumps
		report_lines.append("ALL PUMPS SUMMARY:")
		report_lines.append("-" * 80)
		
		for pump_id, result in sorted(results.items()):
			status = "🔴 CRITICAL" if result.minutes_to_threshold and result.minutes_to_threshold < 15 else "🟢 OK"
			time_str = f"{result.minutes_to_threshold:.1f} min" if result.minutes_to_threshold else "Cooling"
			report_lines.append(f"{status} | Pump {str(pump_id)[:8]}... | Temp: {result.current_temperature:6.1f}°C | "
			                   f"Slope: {result.temperature_slope:7.4f}°C/min | TTF: {time_str:>10}")
		
		return "\n".join(report_lines)


__all__ = ['TrendAnalyzer', 'TrendAnalysisResult', 'TemperatureReading']
