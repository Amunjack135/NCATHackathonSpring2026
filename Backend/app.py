import atexit

import datetime
import flask
import sys
import threading
import time
import typing
import waitress

import CustomMethodsVI.Connection as Connection
import CustomMethodsVI.Logger as Logger

import APIHandler
import Simulation
import SocketHandler


# Server Setup
logger: Logger.Logger = Logger.Logger(sys.stdout, datetime.datetime.now().astimezone().tzinfo)
oil_field_simulation: Simulation.MyOilFieldSimulation = Simulation.MyOilFieldSimulation()
app: flask.Flask = flask.Flask(__name__)
server: Connection.FlaskSocketioServer = Connection.FlaskSocketioServer(app)
api_closer: typing.Callable[[], None] = APIHandler.init(server, logger, oil_field_simulation)
socket_closer: typing.Callable[[], None] = SocketHandler.init(server, logger)

# Oil Pump Setup

for i in range(8):
	oil_field_simulation.add_oil_pump()


# Flask routes
@app.route('/')
def index() -> flask.Response:
	return flask.Response('INDEX.HTML')


@app.route('/health')
def health() -> flask.Response:
	return flask.Response('OK', status=200)


# Main program code
def main() -> None:
	"""
	*Main entry point*
	Starts the server
	"""

	logger.info('\033[38;2;50;255;50m[*] Server Started\033[0m')
	waitress.serve(app, port=8080)
	simulation_flag.set()


def simulate(event: threading.Event) -> None:
	"""
	Simulates the oil field and all pumps
	:param event: The threading event to close this thread
	"""

	try:
		logger.info('\033[38;2;50;255;50m[*] Oil field simulation started\033[0m')

		while not event.is_set():
			oil_field_simulation.tick()
			time.sleep(1 / 60)
	except KeyboardInterrupt:
		pass
	finally:
		logger.info('\033[38;2;255;50;50m[!] Oil filed simulation stopped\033[0m')


def finalize() -> None:
	"""
	Closes the server, cleaning all resources
	"""

	logger.info('\033[38;5;214m[!] Server Closing...\033[0m')
	api_closer()
	socket_closer()
	simulation_flag.set()
	simulation_thread.join()
	logger.info('\033[38;2;255;50;50m[!] Server Closed\033[0m')
	logger.detach()


simulation_flag: threading.Event = threading.Event()
simulation_thread: threading.Thread = threading.Thread(target=simulate, args=(simulation_flag,))
simulation_thread.start()
atexit.register(finalize)

if __name__ == '__main__':
	main()
