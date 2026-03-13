import atexit

import datetime
import flask
import sys
import typing
import waitress

import CustomMethodsVI.Connection as Connection
import CustomMethodsVI.Logger as Logger

import SocketHandler


logger: Logger.Logger = Logger.Logger(sys.stdout, datetime.datetime.now().astimezone().tzinfo)
app: flask.Flask = flask.Flask(__name__)
server: Connection.FlaskSocketioServer = Connection.FlaskSocketioServer(app)
socket_closer: typing.Callable[[], None] = SocketHandler.init(server, logger)


@app.route('/')
def index() -> flask.Response:
	return flask.Response('INDEX.HTML')


@app.route('/health')
def health() -> flask.Response:
	return flask.Response('OK', status=200)


def main():
	logger.info('\033[38;2;50;255;50m[*] Server Started\033[0m')
	waitress.serve(app, port=8080)


def finalize() -> None:
	logger.info('\033[38;5;214m[!] Server Closing...\033[0m')
	socket_closer()
	logger.info('\033[38;2;255;50;50m[!] Server Closed\033[0m')
	logger.detach()


atexit.register(finalize)

if __name__ == '__main__':
	main()
