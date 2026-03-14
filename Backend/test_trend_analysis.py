import pytest
import tempfile
import csv
import time
from pathlib import Path
from datetime import datetime, timezone
import uuid

from TrendAnalysis import TrendAnalyzer, TrendAnalysisResult, TemperatureReading


class TestTemperatureReading:
	"""Test TemperatureReading dataclass"""
	
	def test_temperature_reading_creation(self):
		"""Test basic TemperatureReading creation"""
		timestamp = datetime.now(timezone.utc).timestamp()
		reading = TemperatureReading(
			timestamp=timestamp,
			temperature=65.5,
			is_running=True
		)
		
		assert reading.timestamp == timestamp
		assert reading.temperature == 65.5
		assert reading.is_running == True
	
	def test_temperature_reading_not_running(self):
		"""Test TemperatureReading when pump is not running"""
		timestamp = datetime.now(timezone.utc).timestamp()
		reading = TemperatureReading(
			timestamp=timestamp,
			temperature=20.0,
			is_running=False
		)
		
		assert reading.is_running == False
		assert reading.temperature == 20.0


class TestTrendAnalyzer:
	"""Test TrendAnalyzer functionality"""
	
	def test_analyzer_initialization(self):
		"""Test TrendAnalyzer initialization with default and custom parameters"""
		analyzer = TrendAnalyzer()
		assert analyzer.emergency_threshold == 85.0
		assert analyzer.analysis_readings == 10
		
		custom_analyzer = TrendAnalyzer(emergency_threshold=90.0, analysis_readings=20)
		assert custom_analyzer.emergency_threshold == 90.0
		assert custom_analyzer.analysis_readings == 20
	
	def test_read_pump_csv_nonexistent_file(self):
		"""Test reading a non-existent CSV file"""
		analyzer = TrendAnalyzer()
		result = analyzer.read_pump_csv(Path('/nonexistent/path/pump.csv'))
		assert result == []
	
	def test_read_pump_csv_valid_file(self):
		"""Test reading a valid pump CSV file"""
		analyzer = TrendAnalyzer()
		
		with tempfile.TemporaryDirectory() as tmpdir:
			csv_path = Path(tmpdir) / 'test_pump.csv'
			
			# Create a sample CSV file
			with open(csv_path, 'w', newline='') as f:
				writer = csv.writer(f)
				writer.writerow(['Timestamp', 'Temperature', 'Pressure', 'Flow Rate', 'RPM', 
				               'Operational Hours', 'Requires Maintenance', 'Load Percent', 'Is Running'])
				base_time = datetime.now(timezone.utc).timestamp()
				for i in range(5):
					writer.writerow([base_time + i*60, 20.0 + i*5, 100, 10, 1000, i*60, False, 0.5, True])
			
			readings = analyzer.read_pump_csv(csv_path)
			assert len(readings) == 5
			assert readings[0].temperature == 20.0
			assert readings[4].temperature == 40.0
	
	def test_read_pump_csv_with_invalid_rows(self):
		"""Test reading CSV file with some invalid rows"""
		analyzer = TrendAnalyzer()
		
		with tempfile.TemporaryDirectory() as tmpdir:
			csv_path = Path(tmpdir) / 'test_pump.csv'
			
			with open(csv_path, 'w', newline='') as f:
				writer = csv.writer(f)
				writer.writerow(['Timestamp', 'Temperature', 'Pressure', 'Flow Rate', 'RPM', 
				               'Operational Hours', 'Requires Maintenance', 'Load Percent', 'Is Running'])
				base_time = datetime.now(timezone.utc).timestamp()
				writer.writerow([base_time, 20.0, 100, 10, 1000, 0, False, 0.5, True])
				writer.writerow(['invalid', 'not_a_temp', 100, 10, 1000, 0, False, 0.5, True])  # Invalid
				writer.writerow([base_time + 60, 25.0, 100, 10, 1000, 60, False, 0.5, True])
			
			readings = analyzer.read_pump_csv(csv_path)
			# Should have 2 valid readings (invalid row skipped)
			assert len(readings) == 2
			assert readings[0].temperature == 20.0
			assert readings[1].temperature == 25.0
	
	def test_analyze_pump_insufficient_data(self):
		"""Test analyze_pump with insufficient data"""
		analyzer = TrendAnalyzer()
		
		with tempfile.TemporaryDirectory() as tmpdir:
			csv_path = Path(tmpdir) / 'test_pump.csv'
			
			with open(csv_path, 'w', newline='') as f:
				writer = csv.writer(f)
				writer.writerow(['Timestamp', 'Temperature', 'Pressure', 'Flow Rate', 'RPM', 
				               'Operational Hours', 'Requires Maintenance', 'Load Percent', 'Is Running'])
				writer.writerow([datetime.now(timezone.utc).timestamp(), 20.0, 100, 10, 1000, 0, False, 0.5, True])
			
			result = analyzer.analyze_pump(csv_path)
			assert result is None
	
	def test_analyze_pump_cooling_down(self):
		"""Test analyze_pump when temperature is cooling down"""
		analyzer = TrendAnalyzer()
		
		with tempfile.TemporaryDirectory() as tmpdir:
			csv_path = Path(tmpdir) / 'test_pump.csv'
			
			with open(csv_path, 'w', newline='') as f:
				writer = csv.writer(f)
				writer.writerow(['Timestamp', 'Temperature', 'Pressure', 'Flow Rate', 'RPM', 
				               'Operational Hours', 'Requires Maintenance', 'Load Percent', 'Is Running'])
				base_time = datetime.now(timezone.utc).timestamp()
				# Temperature decreasing from 80 to 20
				for i in range(12):
					temp = 80 - i * 5
					writer.writerow([base_time + i*60, temp, 100, 10, 1000, i*60, False, 0.5, False])
			
			result = analyzer.analyze_pump(csv_path)
			assert result is not None
			assert result.current_temperature < 80
			assert result.temperature_slope < 0  # Negative slope = cooling
			assert result.minutes_to_threshold is None  # No failure predicted
	
	def test_analyze_pump_heating_up(self):
		"""Test analyze_pump when temperature is heating up"""
		analyzer = TrendAnalyzer()
		
		with tempfile.TemporaryDirectory() as tmpdir:
			csv_path = Path(tmpdir) / 'test_pump.csv'
			
			with open(csv_path, 'w', newline='') as f:
				writer = csv.writer(f)
				writer.writerow(['Timestamp', 'Temperature', 'Pressure', 'Flow Rate', 'RPM', 
				               'Operational Hours', 'Requires Maintenance', 'Load Percent', 'Is Running'])
				base_time = datetime.now(timezone.utc).timestamp()
				# Temperature increasing from 20 to 80
				for i in range(12):
					temp = 20 + i * 5
					writer.writerow([base_time + i*60, temp, 100, 10, 1000, i*60, False, 0.5, True])
			
			result = analyzer.analyze_pump(csv_path)
			assert result is not None
			assert result.current_temperature == 75
			assert result.temperature_slope > 0  # Positive slope = heating
			assert result.minutes_to_threshold is not None
			assert result.minutes_to_threshold > 0
	
	def test_analyze_pump_with_custom_threshold(self):
		"""Test analyze_pump with custom emergency threshold"""
		analyzer = TrendAnalyzer(emergency_threshold=60.0)
		
		with tempfile.TemporaryDirectory() as tmpdir:
			csv_path = Path(tmpdir) / 'test_pump.csv'
			
			with open(csv_path, 'w', newline='') as f:
				writer = csv.writer(f)
				writer.writerow(['Timestamp', 'Temperature', 'Pressure', 'Flow Rate', 'RPM', 
				               'Operational Hours', 'Requires Maintenance', 'Load Percent', 'Is Running'])
				base_time = datetime.now(timezone.utc).timestamp()
				for i in range(12):
					temp = 20 + i * 3
					writer.writerow([base_time + i*60, temp, 100, 10, 1000, i*60, False, 0.5, True])
			
			result = analyzer.analyze_pump(csv_path)
			assert result is not None
			assert result.emergency_threshold == 60.0
	
	def test_trend_analysis_result_already_exceeded(self):
		"""Test TrendAnalysisResult when temperature already exceeded threshold"""
		result = TrendAnalysisResult(
			pump_id=uuid.uuid4(),
			current_temperature=90.0,
			temperature_slope=1.0,
			minutes_to_threshold=-2.0,  # Already exceeded
			confidence=0.95,
			readings_count=10,
			emergency_threshold=85.0
		)
		
		prediction = result.get_failure_prediction()
		assert "Already exceeded threshold" in prediction
	
	def test_trend_analysis_result_critical(self):
		"""Test TrendAnalysisResult in critical state"""
		result = TrendAnalysisResult(
			pump_id=uuid.uuid4(),
			current_temperature=84.5,
			temperature_slope=1.0,
			minutes_to_threshold=0.5,  # Less than 1 minute
			confidence=0.95,
			readings_count=10,
			emergency_threshold=85.0
		)
		
		prediction = result.get_failure_prediction()
		assert "CRITICAL" in prediction
		assert "imminent" in prediction
	
	def test_trend_analysis_result_warning(self):
		"""Test TrendAnalysisResult in warning state"""
		result = TrendAnalysisResult(
			pump_id=uuid.uuid4(),
			current_temperature=82.0,
			temperature_slope=0.5,
			minutes_to_threshold=6.0,
			confidence=0.95,
			readings_count=10,
			emergency_threshold=85.0
		)
		
		prediction = result.get_failure_prediction()
		assert "WARNING" in prediction or "approximately" in prediction
	
	def test_trend_analysis_result_safe(self):
		"""Test TrendAnalysisResult in safe state"""
		result = TrendAnalysisResult(
			pump_id=uuid.uuid4(),
			current_temperature=40.0,
			temperature_slope=-0.1,
			minutes_to_threshold=None,
			confidence=0.95,
			readings_count=10,
			emergency_threshold=85.0
		)
		
		prediction = result.get_failure_prediction()
		assert "cooling down" in prediction or "stable" in prediction
	
	def test_analyze_all_pumps(self):
		"""Test analyze_all_pumps with multiple pump files"""
		analyzer = TrendAnalyzer()
		
		with tempfile.TemporaryDirectory() as tmpdir:
			data_dir = Path(tmpdir)
			
			# Create 3 pump CSV files with different UUIDs
			pump_ids = [uuid.uuid4() for _ in range(3)]
			
			for pump_id in pump_ids:
				csv_path = data_dir / f'{pump_id}.csv'
				
				with open(csv_path, 'w', newline='') as f:
					writer = csv.writer(f)
					writer.writerow(['Timestamp', 'Temperature', 'Pressure', 'Flow Rate', 'RPM', 
					               'Operational Hours', 'Requires Maintenance', 'Load Percent', 'Is Running'])
					base_time = datetime.now(timezone.utc).timestamp()
					for i in range(12):
						temp = 20 + i * 4  # Increasing temperature
						writer.writerow([base_time + i*60, temp, 100, 10, 1000, i*60, False, 0.5, True])
			
			results = analyzer.analyze_all_pumps(data_dir)
			
			assert len(results) == 3
			for pump_id in pump_ids:
				assert pump_id in results
				assert results[pump_id] is not None
	
	def test_get_critical_pumps(self):
		"""Test get_critical_pumps filtering"""
		analyzer = TrendAnalyzer()
		
		# Create sample results
		results = {}
		
		# Pump 1: Critical (failure in 5 minutes)
		results[uuid.uuid4()] = TrendAnalysisResult(
			pump_id=uuid.uuid4(),
			current_temperature=82.0,
			temperature_slope=0.6,
			minutes_to_threshold=5.0,
			confidence=0.95,
			readings_count=10,
			emergency_threshold=85.0
		)
		
		# Pump 2: Not critical (failure in 30 minutes)
		results[uuid.uuid4()] = TrendAnalysisResult(
			pump_id=uuid.uuid4(),
			current_temperature=70.0,
			temperature_slope=0.5,
			minutes_to_threshold=30.0,
			confidence=0.95,
			readings_count=10,
			emergency_threshold=85.0
		)
		
		# Pump 3: Cooling down (no failure)
		results[uuid.uuid4()] = TrendAnalysisResult(
			pump_id=uuid.uuid4(),
			current_temperature=60.0,
			temperature_slope=-0.5,
			minutes_to_threshold=None,
			confidence=0.95,
			readings_count=10,
			emergency_threshold=85.0
		)
		
		critical = analyzer.get_critical_pumps(results, minutes_warning=15.0)
		
		# Only the first pump should be critical
		assert len(critical) == 1
		assert critical[0].minutes_to_threshold == 5.0
	
	def test_get_critical_pumps_sorted(self):
		"""Test that critical pumps are sorted by time to failure"""
		analyzer = TrendAnalyzer()
		
		pump_ids = [uuid.uuid4() for _ in range(3)]
		results = {}
		
		# Create pumps with different failure times (out of order)
		failure_times = [3.0, 12.0, 1.5]
		
		for i, (pump_id, fail_time) in enumerate(zip(pump_ids, failure_times)):
			results[pump_id] = TrendAnalysisResult(
				pump_id=pump_id,
				current_temperature=82.0 + i,
				temperature_slope=1.0,
				minutes_to_threshold=fail_time,
				confidence=0.95,
				readings_count=10,
				emergency_threshold=85.0
			)
		
		critical = analyzer.get_critical_pumps(results, minutes_warning=15.0)
		
		# Should be sorted by time to failure (ascending)
		assert len(critical) == 3
		assert critical[0].minutes_to_threshold == 1.5
		assert critical[1].minutes_to_threshold == 3.0
		assert critical[2].minutes_to_threshold == 12.0
	
	def test_generate_report(self):
		"""Test report generation"""
		analyzer = TrendAnalyzer()
		
		pump_id = uuid.uuid4()
		result = TrendAnalysisResult(
			pump_id=pump_id,
			current_temperature=82.5,
			temperature_slope=0.75,
			minutes_to_threshold=3.33,
			confidence=0.98,
			readings_count=10,
			emergency_threshold=85.0
		)
		
		report = analyzer.generate_report({pump_id: result})
		
		assert "PUMP TREND ANALYSIS REPORT" in report
		assert "1" in report  # Total pumps
		assert str(pump_id)[:8] in report
		assert "82.5" in report
		assert "0.75" in report
	
	def test_generate_report_empty(self):
		"""Test report generation with no data"""
		analyzer = TrendAnalyzer()
		report = analyzer.generate_report({})
		
		assert "No pump data available" in report


class TestCSVIntegration:
	"""Integration tests for CSV reading and analysis"""
	
	def test_full_csv_pipeline(self):
		"""Test the complete pipeline: CSV -> Read -> Analyze -> Report"""
		analyzer = TrendAnalyzer(emergency_threshold=85.0)
		
		with tempfile.TemporaryDirectory() as tmpdir:
			data_dir = Path(tmpdir)
			
			# Create a realistic pump CSV
			pump_id = uuid.uuid4()
			csv_path = data_dir / f'{pump_id}.csv'
			
			with open(csv_path, 'w', newline='') as f:
				writer = csv.writer(f)
				writer.writerow(['Timestamp', 'Temperature', 'Pressure', 'Flow Rate', 'RPM', 
				               'Operational Hours', 'Requires Maintenance', 'Load Percent', 'Is Running'])
				
				base_time = datetime.now(timezone.utc).timestamp()
				# Simulate pump heating up over 20 minutes
				for i in range(20):
					temp = 30 + i * 2.5  # Increasing at 2.5°C per minute
					pressure = 100 + i * 5
					writer.writerow([
						base_time + i*60,  # Timestamp (every minute)
						temp,
						pressure,
						10 + i * 0.2,
						1000 + i * 50,
						i * 0.5,
						False,
						0.5 + i * 0.01,
						True
					])
			
			# Analyze all pumps
			results = analyzer.analyze_all_pumps(data_dir)
			
			assert pump_id in results
			result = results[pump_id]
			
			# Verify the analysis
			assert result.current_temperature > 30  # Should be hot near end
			assert result.temperature_slope > 0  # Should be heating
			assert result.minutes_to_threshold is not None  # Should predict failure
			assert result.minutes_to_threshold > 0
			
			# Generate report
			report = analyzer.generate_report(results)
			assert "PUMP TREND ANALYSIS REPORT" in report
			assert str(pump_id)[:8] in report


if __name__ == '__main__':
	pytest.main([__file__, '-v'])
