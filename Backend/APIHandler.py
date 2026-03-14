import datetime
import string
import typing
import uuid

import CustomMethodsVI.Connection as Connection
import CustomMethodsVI.Logger as Logger

import Simulation


def init(server: Connection.FlaskSocketioServer, logger: Logger.Logger, simulation: Simulation.MyOilFieldSimulation) -> typing.Callable[[], None]:
	"""
	Initializes the API gateway
	:param server: The flask server
	:param logger: The logger stream
	:param simulation: The oil field simulation
	:return: The closer to close API gateway
	"""

	api: Connection.FlaskServerAPI = Connection.FlaskServerAPI(server.app, '/api', requires_auth=True)

	@api.connector
	def on_api_connect(session: Connection.FlaskServerAPI.APISessionInfo, request: dict) -> int:
		"""
		Callback for API connect
		:param session: Connection request session
		:param request: Connection request body
		:return: HTTP response code
		"""

		logger.info(f'\033[38;2;50;50;255m[*] API session connected with new token {session.token}\033[0m')
		return 200

	@api.disconnector
	def on_api_disconnect(session: Connection.FlaskServerAPI.APISessionInfo, request: dict) -> None:
		"""
		Callback for API disconnect
		:param session: Disconnection request session
		:param request: Disconnection request body
		"""

		logger.info(f'\033[38;2;255;50;255m[*] API session disconnected ({session.token})\033[0m')
		return

	@api.endpoint('/pumps')
	def on_api_pumps(session: Connection.FlaskServerAPI.APISessionInfo, request: dict) -> dict[str, float]:
		"""
		*API endpoint*
		Sends all pump IDs in the oil field
		:param session: The API session
		:param request: The request body
		:return: A mapping of all pumps and their estimated health
		"""

		return {str(pump.uuid): pump.get_estimated_pump_state() for pump in simulation.pumps}

	@api.endpoint('/pump-status')
	def on_api_pump_status(session: Connection.FlaskServerAPI.APISessionInfo, request: dict) -> int | dict[str, float | str | bool]:
		"""
		*API endpoint*
		Gets detailed information about the specified pump
		:param session: The API session
		:param request: The request body
		:return: A mapping of all pump values
		"""

		request_pump_id: str = request.get('pump-id')

		if not isinstance(request_pump_id, str) and all(c in string.hexdigits for c in request_pump_id):
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

		request_pump_id: str = request.get('pump-id')
		request_override: bool = request.get('override')

		if (not isinstance(request_pump_id, str) and all(c in string.hexdigits for c in request_pump_id)) or not isinstance(request_override, bool):
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

	@api.endpoint('/pump-stop')
	def on_api_pump_stop(session: Connection.FlaskServerAPI.APISessionInfo, request: dict) -> int | dict[str, bool | str]:
		"""
		*API endpoint*
		Stops a pump
		:param session: The API session
		:param request: The request body
		:return: Pump stop response
		"""

		request_pump_id: str = request.get('pump-id')

		if (not isinstance(request_pump_id, str) and all(c in string.hexdigits for c in request_pump_id)):
			return 400

		target_pump_id: uuid.UUID = uuid.UUID(hex=request_pump_id)
		pump: typing.Optional[Simulation.MyOilPump] = simulation.get_oil_pump(target_pump_id)

		if pump is None:
			return {'error': 'no-such-pump', 'pump-id': request_pump_id}
		elif not pump.is_running:
			return {'result': False, 'stop-message': 'Pump Already Stopped'}
		else:
			return {'result': True, 'start-message': 'Pump Stopped'}

	def closer() -> None:
		"""
		Closes the API gateway
		"""

		logger.info(f'\033[38;2;255;50;50m[!] API handler deinitialized\033[0m')

	logger.info(f'\033[38;2;50;255;50m[*] API handler initialized at {api.__route__}\033[0m')
	return closer


__all__: list[str] = ['init']
