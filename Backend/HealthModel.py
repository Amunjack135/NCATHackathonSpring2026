import datetime
import random
import time
import typing
import uuid

from HealthModel import PumpHealthAnalyzer
from pump_analyzer import analyze_pump

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
ERROR_ADDITION_PER_TICK: float = 0.25
MAX_METRIC_STORE_TASK: float = 3600


class MyOilPump:

    def __init__(self, pump_id: uuid.UUID, temperature: float, vibration: float, pressure: float, flow_rate: float, rpm: float, operational_hours: float, requires_maintenance: bool, load_percent: float):

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

        self.__health_analyzer__: PumpHealthAnalyzer = PumpHealthAnalyzer(window_size=10)

        self.__runtime_metrics__: dict[datetime.datetime, tuple[float | bool, ...]] = {}

        # store AI analysis history
        self.__analysis_history__: list[dict] = []

        # run analyzer every N ticks instead of every tick
        self.__analysis_tick_counter__: int = 0
        self.__analysis_interval__: int = 10

    def start_pump(self) -> None:
        self.__running__ = True

    def stop_pump(self) -> None:
        self.__running__ = False

    def analyze(self):
        """
        Send current telemetry to pump_analyzer
        """

        pump_data = {
            "pump_id": str(self.uuid),
            "temperature": self.temperature,
            "pressure": self.pressure,
            "flow_rate": self.flow_rate,
            "rpm": self.rpm,
            "load_percent": self.load_percent,
            "vibration": self.vibration,
            "operational_hours": self.operational_hours,
            "is_running": self.is_running,
            "requires_maintenance": self.requires_maintenance
        }

        try:
            result = analyze_pump(pump_data)
            return result
        except Exception as e:
            print(f"Analyzer error for pump {self.uuid}: {e}")
            return None

    def tick(self, now: datetime.datetime, time_delta_seconds: float) -> None:

        if random.random() < BASE_ERROR_CHANCE:
            self.__error_ratio__ = 1

        if 0 <= self.__error_ratio__ <= MAX_ERROR_TICK:
            self.__error_ratio__ += 1

        error_multiplier: float = ((1 + ERROR_ADDITION_PER_TICK) * min(1., (self.__error_ratio__ / MAX_ERROR_TICK))) if self.__error_ratio__ > 0 else 1

        target_temperature: float = ((85 * error_multiplier) if self.is_running else BASE_TEMPERATURE) + (random.random() - 1) * 25.7
        target_pressure: float = ((205.4 * error_multiplier) if self.is_running else 100) + (random.random() - 1) * 58.2
        target_flow_rate: float = ((11.2 * error_multiplier) if self.is_running else 0) + (random.random() - 1) * 5.8
        target_rpm: float = ((2150 * error_multiplier) if self.is_running else 0) + (random.random() - 1) * 650
        target_load_percent: float = ((0.95 * error_multiplier) if self.is_running else 0) + (random.random() - 1)
        target_vibration: float = ((2.95 * error_multiplier) if self.is_running else 0) + (random.random() - 1) * 1.45

        self.__temperature__ += (target_temperature - self.__temperature__) * TEMPERATURE_SCALAR
        self.__pressure__ += (target_pressure - self.__pressure__) * PRESSURE_SCALAR
        self.__flow_rate__ += (target_flow_rate - self.__flow_rate__) * FLOW_RATE_SCALAR
        self.__rpm__ += (target_rpm - self.__rpm__) * RPM_SCALAR
        self.__load_percent__ += (target_load_percent - self.__load_percent__) * LOAD_PERCENT_SCALAR
        self.__vibration__ += (target_vibration - self.__vibration__) * VIBRATION_SCALAR

        self.__operational_hours__ += time_delta_seconds

        health: float = self.get_estimated_pump_state()

        self.__runtime_metrics__[now] = (
            self.temperature,
            self.pressure,
            self.flow_rate,
            self.rpm,
            self.load_percent,
            self.vibration,
            self.operational_hours,
            health,
            self.is_running,
            self.requires_maintenance
        )

        if health < 0.25:
            self.stop_pump()

        # increment tick counter
        self.__analysis_tick_counter__ += 1

        # run AI analysis every configured interval
        if self.__analysis_tick_counter__ % self.__analysis_interval__ == 0:

            analysis = self.analyze()

            if analysis:

                self.__analysis_history__.append({
                    "timestamp": now,
                    "analysis": analysis
                })

                print(
                    f"[AI Decision] Pump {self.uuid} | "
                    f"Temp: {self.temperature:.2f}C | "
                    f"Health: {health:.2f} | "
                    f"Result: {analysis}"
                )

                if isinstance(analysis, dict) and analysis.get("severity") == "critical":
                    print(f"CRITICAL FAILURE RISK detected for pump {self.uuid}")
                    self.__requires_maintenance__ = True

        closed_metrics: list[datetime.datetime] = []

        for stamp in self.__runtime_metrics__:
            if (now - stamp).total_seconds() > MAX_METRIC_STORE_TASK:
                closed_metrics.append(stamp)

        for stamp in closed_metrics:
            del self.__runtime_metrics__[stamp]

    def move_to_error_state(self) -> None:
        self.__error_ratio__ = 1

    def get_estimated_pump_state(self) -> float:

        health_metrics = self.__health_analyzer__.calculate_health(
            temperature=self.__temperature__,
            vibration=self.__vibration__,
            load_percent=self.__load_percent__,
            operational_hours=self.__operational_hours__
        )

        return health_metrics.overall_health

    def get_health_metrics(self):

        return self.__health_analyzer__.calculate_health(
            temperature=self.__temperature__,
            vibration=self.__vibration__,
            load_percent=self.__load_percent__,
            operational_hours=self.__operational_hours__
        )

    def predict_failure(self):

        return self.__health_analyzer__.predict_failure(
            temperature=self.__temperature__,
            vibration=self.__vibration__,
            load_percent=self.__load_percent__,
            operational_hours=self.__operational_hours__
        )

    @property
    def uuid(self) -> uuid.UUID:
        return self.__uuid__

    @property
    def temperature(self) -> float:
        return self.__temperature__

    @property
    def pressure(self) -> float:
        return self.__pressure__

    @property
    def flow_rate(self) -> float:
        return self.__flow_rate__

    @property
    def rpm(self) -> float:
        return self.__rpm__

    @property
    def operational_hours(self) -> float:
        return self.__operational_hours__

    @property
    def requires_maintenance(self) -> bool:
        return self.__requires_maintenance__

    @property
    def load_percent(self) -> float:
        return self.__load_percent__

    @property
    def vibration(self) -> float:
        return self.__vibration__

    @property
    def is_running(self) -> bool:
        return self.__running__


class MyOilFieldSimulation:

    def __init__(self):
        self.__pumps__: dict[uuid.UUID, MyOilPump] = {}
        self.__last_tick__: float = ...

    def __len__(self) -> int:
        return len(self.__pumps__)

    def tick(self) -> None:

        time_point: float = time.perf_counter()
        time_delta: float = 0 if self.__last_tick__ is ... else (time_point - self.__last_tick__)
        now: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)
        self.__last_tick__ = time_point

        for pump in self.__pumps__.values():
            pump.tick(now, time_delta)

    def add_oil_pump(self, *, temperature: float = BASE_TEMPERATURE, vibration: float = 0, pressure: float = BASE_PRESSURE, flow_rate: float = 0, rpm: float = 0, operational_hours: float = 0, requires_maintenance: bool = False, load_percent: float = 0) -> uuid.UUID:

        uid: uuid.UUID = uuid.uuid4()

        while uid in self.__pumps__:
            uid = uuid.uuid4()

        self.__pumps__[uid] = MyOilPump(uid, temperature, vibration, pressure, flow_rate, rpm, operational_hours, requires_maintenance, load_percent)

        return uid

    def get_oil_pump(self, pump_id: uuid.UUID) -> typing.Optional[MyOilPump]:
        return self.__pumps__.get(pump_id, None)

    @property
    def pumps(self) -> typing.Iterator[MyOilPump]:
        for pump in self.__pumps__.values():
            yield pump


__all__: list[str] = ['MyOilPump', 'MyOilFieldSimulation']
