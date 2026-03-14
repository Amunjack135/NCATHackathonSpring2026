import atexit

import datetime
import flask
import sys
import threading
import time
import typing
import uuid
import waitress

import CustomMethodsVI.Connection as Connection
import CustomMethodsVI.FileSystem as FileSystem
import CustomMethodsVI.Logger as Logger
import CustomMethodsVI.Stream as Stream

import APIHandler
import Simulation
import SocketHandler


# Server Setup
ROOT: FileSystem.Directory = FileSystem.File(__file__).parent
PUMP_CSV_SAVE_TIME: float = 30
LOG_DIRECTORY: FileSystem.Directory = ROOT.cd('logs')
LOGFILE: FileSystem.File = LOG_DIRECTORY.file('latest.log')
LOGSTREAM: Stream.FileStream = LOGFILE.open('w')

event_stream: Stream.EventedStream[str] = Stream.EventedStream()
line: list[str] = []


@event_stream.on('write')
def on_std_write(msg: str) -> None:
	for c in msg:
		line.append(c)

		if c == '\n':
			data: str = ''.join(line)
			line.clear()
			sys.stdout.write(data)
			LOGSTREAM.write(data)
			LOGSTREAM.flush()


logger: Logger.Logger = Logger.Logger(event_stream, datetime.datetime.now().astimezone().tzinfo)
pump_data_directory: FileSystem.Directory = ROOT.cd('/data/pumps')
oil_field_simulation: Simulation.MyOilFieldSimulation = Simulation.MyOilFieldSimulation()
app: flask.Flask = flask.Flask(__name__)
server: Connection.FlaskSocketioServer = Connection.FlaskSocketioServer(app)
api_closer: typing.Callable[[], None] = APIHandler.init(server, logger, oil_field_simulation)
socket_closer: typing.Callable[[], None] = SocketHandler.init(server, logger)


# Flask routes
@app.route('/')
def index() -> flask.Response:
	return flask.Response('INDEX.HTML')


@app.route('/health')
def health() -> flask.Response:
	return flask.Response('OK', status=200)


@app.route('/logs')
def logs() -> flask.Response:
	return flask.Response(LOGFILE.single_read().replace('\n', '<br />'), status=200)


# Main program code
@app.after_request
def on_response(response: flask.Response) -> flask.Response:
	response.headers['Access-Control-Allow-Origin'] = '*'
	response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
	response.headers['Access-Control-Allow-Headers'] = '*'
	return response


def main() -> None:
	"""
	*Main entry point*
	Starts the server
	"""

	logger.info('\033[38;2;50;255;50m[*] Server Started\033[0m')
	waitress.serve(app, port=443)
	simulation_flag.set()


def simulate(event: threading.Event) -> None:
	"""
	Simulates the oil field and all pumps
	:param event: The threading event to close this thread
	"""

	pump_data_files: dict[uuid.UUID, Stream.FileStream] = {}

	try:
		for i in range(8):
			oil_field_simulation.add_oil_pump()

		if not pump_data_directory.exists():
			pump_data_directory.create()
		else:
			for file in pump_data_directory.files:
				file.delete()

		for pump in oil_field_simulation.pumps:
			file: FileSystem.File = pump_data_directory.file(f'{pump.uuid}.csv')
			fstream: Stream.FileStream = file.open('w')
			pump_data_files[pump.uuid] = fstream
			fstream.write('Timestamp,Temperature,Pressure,Flow Rate,RPM,Operational Hours,Requires Maintenance,Load Percent,Is Running\n')
			fstream.flush()

		logger.info('\033[38;2;50;255;50m[*] Oil field simulation started\033[0m')
		csv_save_time: float = time.perf_counter() - PUMP_CSV_SAVE_TIME

		while not event.is_set():
			oil_field_simulation.tick()

			if time.perf_counter() - csv_save_time >= PUMP_CSV_SAVE_TIME:
				csv_save_time = time.perf_counter()
				save_time: float = datetime.datetime.now(datetime.timezone.utc).timestamp()

				for pump in oil_field_simulation.pumps:
					fstream: Stream.FileStream = pump_data_files[pump.uuid]
					fstream.write(f'{save_time},{pump.temperature},{pump.pressure},{pump.flow_rate},{pump.rpm},{pump.operational_hours},{pump.requires_maintenance},{pump.load_percent},{pump.is_running}\n')
					fstream.flush()

				logger.info(f'\033[38;2;50;255;255m[*] Saved {len(oil_field_simulation)} pumps to CSV files @ {pump_data_directory.abspath}\033[0m')

			time.sleep(1 / 60)

	except KeyboardInterrupt:
		pass
	finally:
		save_time: float = datetime.datetime.now(datetime.timezone.utc).timestamp()

		for pump in oil_field_simulation.pumps:
			fstream: Stream.FileStream = pump_data_files[pump.uuid]
			fstream.write(f'{save_time},{pump.temperature},{pump.pressure},{pump.flow_rate},{pump.rpm},{pump.operational_hours},{pump.requires_maintenance},{pump.load_percent},{pump.is_running}\n')
			fstream.flush()

		for fstream in pump_data_files.values():
			fstream.close()

		logger.info(f'\033[38;2;50;255;255m[*] Saved {len(oil_field_simulation)} pumps to CSV files @ {pump_data_directory.abspath}\033[0m')
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
	event_stream.write('\n')
	LOGSTREAM.flush()
	LOGSTREAM.close()


simulation_flag: threading.Event = threading.Event()
simulation_thread: threading.Thread = threading.Thread(target=simulate, args=(simulation_flag,))
simulation_thread.start()
atexit.register(finalize)

if __name__ == '__main__':
	main()
