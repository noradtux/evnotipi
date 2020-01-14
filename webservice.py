from gevent import monkey, sleep
monkey.patch_all()
from bottle import Bottle, static_file, request
from threading import Thread, Condition
from gevent.pywsgi import WSGIServer
from geventwebsocket import WebSocketError
from geventwebsocket.handler import WebSocketHandler
import json
import logging

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

        self.route('/live/websocket', callback = self.handle_websocket)
        self.route('/', callback = self.handle_index)
        self.route('/static/<filename>', callback = self.handle_static)
        self.route('/data', callback = self.handle_data)

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
        self.server = WSGIServer(("localhost", 8080), self, handler_class=WebSocketHandler)
        self.thread = Thread(target = self.server.serve_forever)
        self.thread.start()
        self.car.registerData(self.dataCallback)

    def stop(self):
        self.car.unregisterData(self.dataCallback)
        self.running = False
        self.server.stop()
        self.server.close()
        self.thread.join()

    def dataCallback(self, data):
        with self.data_lock:
            self.data = data
            self.data_lock.notify_all()

    def checkWatchdog(self):
        return self.thread.is_alive()


if __name__ == '__main__':
    class TestCar:
        def registerData(self, callback):
            self.callback = callback

        def unregisterData(self, callback):
            pass

    from time import sleep

    car = TestCar()
    web = WebService({}, car)
    web.start()

    print("running")
    i = 0
    while True:
        car.callback({'value':i,'bla':i**2})
        i += 1
        sleep(1)
