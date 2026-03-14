import random
import time
import typing
import uuid


BASE_ERROR_CHANCE: float = 0.025
BASE_TEMPERATURE: float = 20
BASE_PRESSURE: float = 1
MAX_ERROR_TICK: int = 300
TEMPERATURE_SCALAR: float = 0.1
PRESSURE_SCALAR: float = 0.05
FLOW_RATE_SCALAR: float = 0.001
RPM_SCALAR: float = 0.5
LOAD_PERCENT_SCALAR: float = 0.5
VIBRATION_SCALAR: float = 0.25
MAXIMUM_HEALTH_THRESHOLD: float = 0.825


class MyOilPump:
	def __init__(self, pump_id: uuid.UUID, temperature: float, vibration: float, pressure: float, flow_rate: float, rpm: float, operational_hours: float, requires_maintenance: bool, load_percent: float):
		"""
		Virtual oil pump object
		:param pump_id: The pump ID
		:param temperature: The pump initial temperature
		:param vibration: The pump initial vibration
		:param pressure: The pump initial pressure
		:param flow_rate: The pump initial flow rate
		:param rpm: The pump initial RPM
		:param operational_hours: The pump initial operational hours
		:param requires_maintenance: The pump maintenance flag
		:param load_percent: The pump initial load percent
		"""

		self.__uuid__: uuid.UUID = pump_id
		self.__temperature__: float = float(temperature)
		self.__pressure__: float = float(pressure)
		self.__flow_rate__: float = float(flow_rate)
		self.__rpm__: float = float(rpm)
		self.__load_percent__: float = float(load_percent)
		self.__vibration__: float = float(vibration)
		self.__operational_hours__: float = float(operational_hours)
		self.__requires_maintenance__: bool = bool(requires_maintenance)
		self.__running__: bool = False
		self.__error_ratio__: int = 0

	def start_pump(self) -> None:
		"""
		Starts the pump
		"""

		self.__running__ = True

	def stop_pump(self) -> None:
		"""
		Stops the pump
		"""

		self.__running__ = False

	def tick(self, time_delta_seconds: float) -> None:
		"""
		Ticks the pump
		All internal values are updated
		:param time_delta_seconds: The time since last tick in seconds
		"""

		if random.random() < BASE_ERROR_CHANCE:
			self.__error_ratio__ = 1

		if 0 <= self.__error_ratio__ <= MAX_ERROR_TICK:
			self.__error_ratio__ += 1

		error_multiplier: float = (2.5 * min(1., (self.__error_ratio__ / MAX_ERROR_TICK))) if self.__error_ratio__ > 0 else 1
		target_temperature: float = (85 if self.is_running else BASE_TEMPERATURE) + (random.random() - 0.5) * 25.7 * error_multiplier
		target_pressure: float = (205.4 if self.is_running else 100) + (random.random() - 0.5) * 58.2 * error_multiplier
		target_flow_rate: float = (11.2 if self.is_running else 0) + (random.random() - 0.5) * 5.8 * error_multiplier
		target_rpm: float = (2150 if self.is_running else 0) + (random.random() - 0.5) * 650 * error_multiplier
		target_load_percent: float = (0.95 if self.is_running else 0) + (random.random() - 0.5) * error_multiplier
		target_vibration: float = (2.95 if self.is_running else 0) + (random.random() - 0.5) * 1.45 * error_multiplier

		self.__temperature__ += (target_temperature - self.__temperature__) * TEMPERATURE_SCALAR
		self.__pressure__ += (target_pressure - self.__pressure__) * PRESSURE_SCALAR
		self.__flow_rate__ += (target_flow_rate - self.__flow_rate__) * FLOW_RATE_SCALAR
		self.__rpm__ += (target_rpm - self.__rpm__) * RPM_SCALAR
		self.__load_percent__ += (target_load_percent - self.__load_percent__) * LOAD_PERCENT_SCALAR
		self.__vibration__ += (target_vibration - self.__vibration__) * VIBRATION_SCALAR

		self.__operational_hours__ += time_delta_seconds

	def get_estimated_pump_state(self) -> float:
		"""
		Gets the estimated health of the pump (between 0 and 1) based on all pump values
		:return: The pump health
		"""

		pass

	@property
	def uuid(self) -> uuid.UUID:
		"""
		:return: The pump ID
		"""

		return self.__uuid__

	@property
	def temperature(self) -> float:
		"""
		:return: The current pump temperature
		"""

		return self.__temperature__

	@property
	def pressure(self) -> float:
		"""
		:return: The current pump pressure
		"""

		return self.__pressure__

	@property
	def flow_rate(self) -> float:
		"""
		:return: The current pump flow-rate
		"""

		return self.__flow_rate__

	@property
	def rpm(self) -> float:
		"""
		:return: The current pump RPM
		"""

		return self.__rpm__

	@property
	def operational_hours(self) -> float:
		"""
		:return: The current pump running hours
		"""

		return self.__operational_hours__

	@property
	def requires_maintenance(self) -> bool:
		"""
		:return: Whether the pump requires maintenance
		"""

		return self.__requires_maintenance__

	@property
	def load_percent(self) -> float:
		"""
		:return: The current pump load percent
		"""

		return self.__load_percent__

	@property
	def is_running(self) -> bool:
		"""
		:return: Whether the pump is running
		"""

		return self.__running__


class MyOilFieldSimulation:
	def __init__(self):
		"""
		Simulates an array of oil pumps
		"""

		self.__pumps__: dict[uuid.UUID, MyOilPump] = {}
		self.__last_tick__: float = ...

	def __len__(self) -> int:
		"""
		:return: The number of pumps in this field
		"""

		return len(self.__pumps__)

	def tick(self) -> None:
		"""
		Ticks the simulation once
		"""

		time_point: float = time.perf_counter()
		time_delta: float = 0 if self.__last_tick__ is ... else (time_point - self.__last_tick__)
		self.__last_tick__ = time_point

		for pump in self.__pumps__.values():
			pump.tick(time_delta)

	def add_oil_pump(self, *, temperature: float = BASE_TEMPERATURE, vibration: float = 0, pressure: float = BASE_PRESSURE, flow_rate: float = 0, rpm: float = 0, operational_hours: float = 0, requires_maintenance: bool = False, load_percent: float = 0) -> uuid.UUID:
		"""
		Adds an oil pump to this field
		:param temperature: The pump initial temperature
		:param vibration: The pump initial vibration
		:param pressure: The pump initial pressure
		:param flow_rate: The pump initial flow rate
		:param rpm: The pump initial RPM
		:param operational_hours: the pump initial running hours
		:param requires_maintenance: Whether pump requires maintenance
		:param load_percent: THe pump initial load percent
		:return: The new pump UUID
		"""

		uid: uuid.UUID = uuid.uuid4()

		while uid in self.__pumps__:
			uid = uuid.uuid4()

		self.__pumps__[uid] = MyOilPump(uid, temperature, vibration, pressure, flow_rate, rpm, operational_hours, requires_maintenance, load_percent)
		return uid

	def get_oil_pump(self, pump_id: uuid.UUID) -> typing.Optional[MyOilPump]:
		"""
		Gets an oil pump by UUID
		:param pump_id: The pump UUID
		:return: The pump
		"""

		return self.__pumps__.get(pump_id, None)

	@property
	def pumps(self) -> typing.Iterator[MyOilPump]:
		"""
		:return: An iterator of all pumps in this field
		"""

		for pump in self.__pumps__.values():
			yield pump


__all__: list[str] = ['MyOilPump', 'MyOilFieldSimulation']
