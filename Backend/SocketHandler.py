import typing
import uuid


import CustomMethodsVI.Connection as Connection
import CustomMethodsVI.Logger as Logger


def init(server: Connection.FlaskSocketioServer, logger: Logger.Logger) -> typing.Callable[[], None]:
	sockets: dict[uuid.UUID, Connection.FlaskSocketioSocket] = {}

	@server.on('connect')
	def on_connect(socket: Connection.FlaskSocketioSocket) -> None:
		socket_id: uuid.UUID = uuid.uuid4()
		sockets[socket_id] = socket

		@socket.on('disconnect')
		def on_disconnect(disconnector: bool) -> None:
			nonlocal socket_id
			del sockets[socket_id]
			socket_id = ...
			logger.info(f'\033[38;2;255;50;255m[*] Socket with UUID {socket_id} disconnected ({socket.ip_address})\033[0m')

		logger.info(f'\033[38;2;50;50;255m[*] Socket connected with new UUID {socket_id} ({socket.ip_address})\033[0m')

	def closer() -> None:
		for uid, socket in sockets.items():
			socket.disconnect()

		logger.info(f'\033[38;2;255;50;50m[!] Socket handler deinitialized\033[0m')

	logger.info(f'\033[38;2;50;255;50m[*] Socket handler initialized\033[0m')
	return closer
