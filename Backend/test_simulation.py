import time
import uuid
import pytest
from Simulation import MyOilFieldSimulation, MyOilPump


class TestMyOilPump:
	"""Test cases for the MyOilPump class"""
	
	def test_pump_initialization(self):
		"""Test that a pump initializes with correct values"""
		pump_id = uuid.uuid4()
		pump = MyOilPump(
			pump_id=pump_id,
			temperature=20.0,
			vibration=0.0,
			pressure=1.0,
			flow_rate=0.0,
			rpm=0.0,
			operational_hours=0.0,
			requires_maintenance=False,
			load_percent=0.0
		)
		
		assert pump.uuid == pump_id
		assert pump.temperature == 20.0
		assert pump.pressure == 1.0
		assert pump.flow_rate == 0.0
		assert pump.rpm == 0.0
		assert pump.operational_hours == 0.0
		assert pump.requires_maintenance == False
		assert pump.is_running == False
	
	def test_pump_start_stop(self):
		"""Test pump start and stop functionality"""
		pump = MyOilPump(
			pump_id=uuid.uuid4(),
			temperature=20.0,
			vibration=0.0,
			pressure=1.0,
			flow_rate=0.0,
			rpm=0.0,
			operational_hours=0.0,
			requires_maintenance=False,
			load_percent=0.0
		)
		
		assert pump.is_running == False
		pump.start_pump()
		assert pump.is_running == True
		pump.stop_pump()
		assert pump.is_running == False
	
	def test_pump_tick_when_running(self):
		"""Test that pump values change when ticking while running"""
		pump = MyOilPump(
			pump_id=uuid.uuid4(),
			temperature=20.0,
			vibration=0.0,
			pressure=1.0,
			flow_rate=0.0,
			rpm=0.0,
			operational_hours=0.0,
			requires_maintenance=False,
			load_percent=0.0
		)
		
		pump.start_pump()
		initial_temp = pump.temperature
		initial_ops_hours = pump.operational_hours
		
		pump.tick(1.0)  # Tick for 1 second
		
		# Temperature should increase when pump is running
		assert pump.temperature != initial_temp
		# Operational hours should increase
		assert pump.operational_hours > initial_ops_hours
	
	def test_pump_tick_when_stopped(self):
		"""Test that pump values stabilize when stopped"""
		pump = MyOilPump(
			pump_id=uuid.uuid4(),
			temperature=50.0,
			vibration=2.0,
			pressure=100.0,
			flow_rate=5.0,
			rpm=1000.0,
			operational_hours=100.0,
			requires_maintenance=False,
			load_percent=0.5
		)
		
		pump.stop_pump()
		initial_temp = pump.temperature
		initial_ops_hours = pump.operational_hours
		
		# Tick multiple times
		for _ in range(10):
			pump.tick(1.0)
		
		# Temperature should move towards base temperature (20)
		assert pump.temperature < initial_temp
		# Operational hours should still increase
		assert pump.operational_hours > initial_ops_hours


class TestMyOilFieldSimulation:
	"""Test cases for the MyOilFieldSimulation class"""
	
	def test_simulation_initialization(self):
		"""Test that simulation initializes correctly"""
		sim = MyOilFieldSimulation()
		pump_count = sum(1 for _ in sim.pumps)
		assert pump_count == 0
	
	def test_add_pump(self):
		"""Test adding pumps to the simulation"""
		sim = MyOilFieldSimulation()
		
		pump_id_1 = sim.add_oil_pump()
		assert pump_id_1 is not None
		assert isinstance(pump_id_1, uuid.UUID)
		
		pump_ids = []
		for _ in range(7):
			pump_ids.append(sim.add_oil_pump())
		
		pump_count = sum(1 for _ in sim.pumps)
		assert pump_count == 8
	
	def test_get_pump(self):
		"""Test retrieving pumps from the simulation"""
		sim = MyOilFieldSimulation()
		pump_id = sim.add_oil_pump()
		
		pumps_list = list(sim.pumps)
		assert len(pumps_list) == 1
		assert isinstance(pumps_list[0], MyOilPump)
	
	def test_get_oil_pump_by_id(self):
		"""Test retrieving a specific pump by ID"""
		sim = MyOilFieldSimulation()
		pump_id = sim.add_oil_pump()
		
		retrieved_pump = sim.get_oil_pump(pump_id)
		assert retrieved_pump is not None
		assert retrieved_pump.uuid == pump_id
	
	def test_simulation_tick(self):
		"""Test that simulation tick updates all pumps"""
		sim = MyOilFieldSimulation()
		
		# Add some pumps
		pump_ids = []
		for _ in range(3):
			pump_ids.append(sim.add_oil_pump())
		
		# Start all pumps
		for pump in sim.pumps:
			pump.start_pump()
		
		# First tick initializes the timer (time_delta will be 0)
		sim.tick()
		
		# Get initial states after first tick
		initial_ops_hours = [pump.operational_hours for pump in sim.pumps]
		
		# Wait a bit and tick the simulation again
		time.sleep(0.01)
		sim.tick()
		
		# All operational hours should have increased (since time passed)
		for i, pump in enumerate(sim.pumps):
			assert pump.operational_hours > initial_ops_hours[i]
	
	def test_multiple_pump_operations(self):
		"""Test operating multiple pumps in simulation"""
		sim = MyOilFieldSimulation()
		
		# Add pumps
		pump_ids = []
		for _ in range(4):
			pump_ids.append(sim.add_oil_pump())
		
		# Start specific pump
		pump_to_start = sim.get_oil_pump(pump_ids[0])
		pump_to_start.start_pump()
		
		assert pump_to_start.is_running == True
		
		# Verify other pumps are not running
		for i in range(1, len(pump_ids)):
			pump = sim.get_oil_pump(pump_ids[i])
			assert pump.is_running == False
	
	def test_prolonged_simulation(self):
		"""Test a prolonged simulation run"""
		sim = MyOilFieldSimulation()
		
		# Add pumps and start them
		for _ in range(8):
			pump_id = sim.add_oil_pump()
			pump = sim.get_oil_pump(pump_id)
			pump.start_pump()
		
		# Run simulation for 100 ticks
		for _ in range(100):
			sim.tick()
			time.sleep(0.001)
		
		# Verify all pumps accumulated operational hours
		for pump in sim.pumps:
			assert pump.operational_hours > 0
			assert pump.is_running == True


class TestIntegration:
	"""Integration tests for the simulation system"""
	
	def test_full_oil_field_cycle(self):
		"""Test a complete oil field operation cycle"""
		sim = MyOilFieldSimulation()
		
		# Setup: Add 8 pumps like in app.py
		pump_ids = []
		for i in range(8):
			pump_ids.append(sim.add_oil_pump())
		
		pump_count = sum(1 for _ in sim.pumps)
		assert pump_count == 8
		
		# Start all pumps
		for pump in sim.pumps:
			pump.start_pump()
		
		# Run for several ticks
		for i in range(60):
			sim.tick()
			time.sleep(0.001)
		
		# Verify pumps are working
		for pump in sim.pumps:
			assert pump.is_running == True
			assert pump.operational_hours > 0
			assert pump.temperature > 0  # Should be heating up
		
		# Stop all pumps
		for pump in sim.pumps:
			pump.stop_pump()
		
		# Run a few more ticks to cool down
		for _ in range(30):
			sim.tick()
			time.sleep(0.001)
		
		# Verify pumps are stopped
		for pump in sim.pumps:
			assert pump.is_running == False


if __name__ == '__main__':
	pytest.main([__file__, '-v'])
