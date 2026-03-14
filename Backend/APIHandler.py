import datetime
import json
import string
import typing
import uuid

import CustomMethodsVI.Connection as Connection
import CustomMethodsVI.Logger as Logger
import CustomMethodsVI.Stream as Stream

import Simulation

import pump_analyzer


def init(server: Connection.FlaskSocketioServer, logger: Logger.Logger, simulation: Simulation.MyOilFieldSimulation) -> typing.Callable[[], None]:
	"""
	Initializes the API gateway
	:param server: The flask server
	:param logger: The logger stream
	:param simulation: The oil field simulation
	:return: The closer to close API gateway
	"""

	api: Connection.FlaskServerAPI = Connection.FlaskServerAPI(server.app, '/api', requires_auth=False)

	@api.endpoint('/pumps')
	def on_api_pumps(session: Connection.FlaskServerAPI.APISessionInfo, request: dict) -> dict[str, float]:
		"""
		*API endpoint*
		Sends all pump IDs in the oil field
		:param session: The API session
		:param request: The request body
		:return: A mapping of all pumps and their estimated health
		"""

		try:
			return {str(pump.uuid): pump.get_estimated_pump_state() for pump in simulation.pumps}
		finally:
			logger.info(f'\033[38;2;255;0;255m[*] API request at \'/pumps\' (REQUEST={request})\033[0m')

	@api.endpoint('/pump-status')
	def on_api_pump_status(session: Connection.FlaskServerAPI.APISessionInfo, request: dict) -> int | dict[str, float | str | bool]:
		"""
		*API endpoint*
		Gets detailed information about the specified pump
		:param session: The API session
		:param request: The request body
		:return: A mapping of the specified pump values
		"""

		try:
			request_pump_id: str = request.get('pump-id')

			if request_pump_id is None or not isinstance(request_pump_id, str) or any(c not in string.hexdigits and c != '-' for c in request_pump_id):
				return 400

			target_pump_id: uuid.UUID = uuid.UUID(hex=request_pump_id)
			pump: typing.Optional[Simulation.MyOilPump] = simulation.get_oil_pump(target_pump_id)

			if pump is None:
				return {'error': 'no-such-pump', 'pump-id': request_pump_id}

			return {
				'pump-id': str(pump.uuid),
				'temperature': pump.temperature,
				'pressure': pump.pressure,
				'flow-rate': pump.flow_rate,
				'rpm': pump.rpm,
				'operational-hours': pump.operational_hours,
				'requires-maintenance': pump.requires_maintenance,
				'load-percent': pump.load_percent,
				'health': pump.get_estimated_pump_state(),
				'is-running': pump.is_running,
				'timestamp': datetime.datetime.now(datetime.timezone.utc).timestamp(),
			}
		finally:
			logger.info(f'\033[38;2;255;0;255m[*] API request at \'/pump-status\' (REQUEST={request})\033[0m')

	@api.endpoint('/pump-statuses')
	def on_api_pump_statuses(session: Connection.FlaskServerAPI.APISessionInfo, request: dict) -> int | dict[str, dict[str, float | str | bool]]:
		"""
		*API endpoint*
		Gets detailed information about all pumps
		:param session: The API session
		:param request: The request body
		:return: A mapping of all pump values
		"""

		try:
			return {str(pump.uuid): {
				'pump-id': str(pump.uuid),
				'temperature': pump.temperature,
				'pressure': pump.pressure,
				'flow-rate': pump.flow_rate,
				'rpm': pump.rpm,
				'operational-hours': pump.operational_hours,
				'requires-maintenance': pump.requires_maintenance,
				'load-percent': pump.load_percent,
				'health': pump.get_estimated_pump_state(),
				'is-running': pump.is_running,
				'timestamp': datetime.datetime.now(datetime.timezone.utc).timestamp(),
			} for pump in simulation.pumps}
		finally:
			logger.info(f'\033[38;2;255;0;255m[*] API request at \'/pump-statuses\' (REQUEST={request})\033[0m')

	@api.endpoint('/pump-start')
	def on_api_pump_start(session: Connection.FlaskServerAPI.APISessionInfo, request: dict) -> int | dict[str, bool | str]:
		"""
		*API endpoint*
		Attempts to start a pump
		If pump health is low, request will be denied unless override enabled
		:param session: The API session
		:param request: The request body
		:return: Pump start response
		"""

		try:
			request_pump_id: str = request.get('pump-id')
			request_override: bool = request.get('override')

			if request_pump_id is None or request_override is None or not isinstance(request_pump_id, str) or any(c not in string.hexdigits and c != '-' for c in request_pump_id) or not isinstance(request_override, bool):
				return 400

			target_pump_id: uuid.UUID = uuid.UUID(hex=request_pump_id)
			pump: typing.Optional[Simulation.MyOilPump] = simulation.get_oil_pump(target_pump_id)

			if pump is None:
				return {'error': 'no-such-pump', 'pump-id': request_pump_id}
			elif pump.is_running:
				return {'result': False, 'start-message': 'Pump Already Started'}
			elif pump.get_estimated_pump_state() < Simulation.MAXIMUM_HEALTH_THRESHOLD or request_override:
				pump.start_pump()
				return {'result': True, 'start-message': 'Pump Started'}
			else:
				return {'result': False, 'start-message': 'Pump Health Low'}
		finally:
			logger.info(f'\033[38;2;255;0;255m[*] API request at \'/pump-start\' (REQUEST={request})\033[0m')

	@api.endpoint('/pump-stop')
	def on_api_pump_stop(session: Connection.FlaskServerAPI.APISessionInfo, request: dict) -> int | dict[str, bool | str]:
		"""
		*API endpoint*
		Stops a pump
		:param session: The API session
		:param request: The request body
		:return: Pump stop response
		"""

		try:
			request_pump_id: str = request.get('pump-id')

			if request_pump_id is None or not isinstance(request_pump_id, str) or any(c not in string.hexdigits and c != '-' for c in request_pump_id):
				return 400

			target_pump_id: uuid.UUID = uuid.UUID(hex=request_pump_id)
			pump: typing.Optional[Simulation.MyOilPump] = simulation.get_oil_pump(target_pump_id)

			if pump is None:
				return {'error': 'no-such-pump', 'pump-id': request_pump_id}
			elif not pump.is_running:
				return {'result': False, 'stop-message': 'Pump Already Stopped'}
			else:
				return {'result': True, 'start-message': 'Pump Stopped'}
		finally:
			logger.info(f'\033[38;2;255;0;255m[*] API request at \'/pump-stop\' (REQUEST={request})\033[0m')

	@api.endpoint('/pump-failure-reason')
	def on_api_pump_failure_reason(session: Connection.FlaskServerAPI.APISessionInfo, request: dict) -> int | dict[str, str]:
		"""
		*API endpoint*
		Gets the AI summary for a pump failure
		:param session: The API session
		:param request: The request body
		:return: Pump failure reason
		"""

		try:
			request_pump_id: str = request.get('pump-id')
			request_timestamp: float = request.get('timestamp')

			if request_pump_id is None or request_timestamp is None or not isinstance(request_pump_id, str) or any(c not in string.hexdigits and c != '-' for c in request_pump_id) or not isinstance(request_timestamp, float) or (request_timestamp := float(request_timestamp)) <= 0:
				return 400

			target_pump_id: uuid.UUID = uuid.UUID(hex=request_pump_id)
			pump: typing.Optional[Simulation.MyOilPump] = simulation.get_oil_pump(target_pump_id)
			metric: typing.Optional[tuple[float | bool, ...]] = pump.get_runtime_metric_for_timestamp(request_timestamp, 1) if pump is not None else pump

			if pump is None:
				return {'error': 'no-such-pump', 'pump-id': request_pump_id}
			elif metric is None:
				return {'error': 'no-such-metric', 'timestamp': request_timestamp}
			else:
				sstream: Stream.StringStream = Stream.StringStream()
				json.dump({
					'pump-id': str(pump.uuid),
					'temperature': metric[0],
					'pressure': metric[1],
					'flow-rate': metric[2],
					'rpm': metric[3],
					'load-percent': metric[4],
					'vibration': metric[5],
					'operational-hours': metric[6],
					'requires-maintenance': metric[8],
					'timestamp': request_timestamp,
					'n-state': metric[7],
					'is-running': metric[9],
				}, sstream)
				summary: str = pump_analyzer.analyze_from_file(sstream)[0]
				return {'summary': summary}
		finally:
			logger.info(f'\033[38;2;255;0;255m[*] API request at \'/pump-failure-reason\' (REQUEST={request})\033[0m')

	@api.endpoint('/move-pump-to-error-state')
	def on_api_move_pump_to_error_state(session: Connection.FlaskServerAPI.APISessionInfo, request: dict) -> int | dict[str, str]:
		"""
		*API endpoint*
		Triggers a runaway error state for the specified pump
		:param session: The API session
		:param request: The request body
		"""

		try:
			request_pump_id: str = request.get('pump-id')

			if request_pump_id is None or not isinstance(request_pump_id, str) or any(c not in string.hexdigits and c != '-' for c in request_pump_id):
				return 400

			target_pump_id: uuid.UUID = uuid.UUID(hex=request_pump_id)
			pump: typing.Optional[Simulation.MyOilPump] = simulation.get_oil_pump(target_pump_id)

			if pump is None:
				return {'error': 'no-such-pump', 'pump-id': request_pump_id, 'result': False}
			elif pump.is_error_flag_set:
				return {'error': 'pump-already-erred', 'pump-id': request_pump_id, 'result': False}
			else:
				pump.move_to_error_state()
				return {'success': 'moved-pump-to-error', 'result': True}
		finally:
			logger.info(f'\033[38;2;255;0;255m[*] API request at \'/move-pump-to-error-state\' (REQUEST={request})\033[0m')

	def closer() -> None:
		"""
		Closes the API gateway
		"""

		logger.info(f'\033[38;2;255;50;50m[!] API handler deinitialized\033[0m')

	logger.info(f'\033[38;2;50;255;50m[*] API handler initialized at {api.__route__}\033[0m')
	return closer


__all__: list[str] = ['init']
