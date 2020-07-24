""" Simple weeb service """
import logging
import json
from geventwebsocket.handler import WebSocketHandler
from geventwebsocket import WebSocketError
from gevent.pywsgi import WSGIServer
from threading import Thread, Condition
from bottle import Bottle, static_file, request
from gevent import monkey, sleep
monkey.patch_all()


class WebService(Bottle):
    def __init__(self, config, car):
        super(WebService, self).__init__()
        self.log = logging.getLogger("EVNotiPi/WebService")
        self.log.info("Initializing WebService")

        self.car = car
        self.data = {}
        self.data_lock = Condition()
        self.running = False
        self.server = None
        self.thread = None

        self.route('/data/live/ws', callback=self.handle_websocket)
        self.route('/data', callback=self.handle_data)
        self.route('/', callback=self.handle_index)
        self.route('/static/<filename>', callback=self.handle_static)

    def handle_websocket(self):
        wsock = request.environ.get('wsgi.websocket')
        if not wsock:
            abort(400, 'Expected WebSocket request.')

        while True:
            try:
                #measurement = json.dumps(queue.get())
                with self.data_lock:
                    self.data_lock.wait()
                    data = self.data
                data = json.dumps(data)
                wsock.send(data)
            except WebSocketError:
                break

    def handle_index(self):
        return static_file('index.html', root="./web")

    def handle_static(self, filename):
        return static_file(filename, root="./web")

    def handle_data(self):
        return json.dumps(self.data)

    def start(self):
        self.running = True
        self.server = WSGIServer(
            ('0.0.0.0', 8080), self, handler_class=WebSocketHandler)
        self.thread = Thread(target=self.server.serve_forever)
        self.thread.start()
        self.car.registerData(self.data_callback)

    def stop(self):
        self.car.unregisterData(self.data_callback)
        self.running = False
        self.server.stop()
        self.server.close()
        self.thread.join()

    def data_callback(self, data):
        with self.data_lock:
            self.data = data
            self.data_lock.notify_all()

    def check_thread(self):
        return self.thread.is_alive()
