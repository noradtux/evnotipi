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

        self.route('/data/live/ws', callback = self.handle_websocket)
        self.route('/data', callback = self.handle_data)
        self.route('/', callback = self.handle_index)
        self.route('/static/<filename>', callback = self.handle_static)

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
        self.server = WSGIServer(('0.0.0.0', 8080), self, handler_class=WebSocketHandler)
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

    data = {"timestamp": 1579030397.4258146, "SOC_BMS": 84.5, "SOC_DISPLAY": 88.5, "auxBatteryVoltage": 14.4, "batteryInletTemperature": 9, "batteryMaxTemperature": 10, "batteryMinTemperature": 9, "cumulativeEnergyCharged": 7334.2, "cumulativeEnergyDischarged": 7073.1, "charging": 1, "normalChargePort": 1, "rapidChargePort": 0, "dcBatteryCurrent": -10.1, "dcBatteryPower": -3.9046600000000002, "dcBatteryVoltage": 386.6, "soh": 100.0, "externalTemperature": 9.0, "latitude": 53.6, "longitude": 9.8, "speed": 13.0, "fix_mode": 3, "CAPACITY": 28, "SLOW_SPEED": 2.3, "NORMAL_SPEED": 4.6, "FAST_SPEED": 50.0, "odo": 42927.0, "cumulativeChargeCurrent": 19950.1, "cumulativeDischargeCurrent": 19881.6, "batteryAvgTemperature": 9.833333333333334, "driveMotorSpeed": 0, "fanStatus": 0, "fanFeedback": 0, "availableChargePower": 76.53, "availableDischargePower": 98.0, "obdVoltage": 14.4, "cellTemp01": 10.0, "cellTemp02": 10.0, "cellTemp03": 10.0, "cellTemp04": 10.0, "cellTemp05": 9.0, "cellTemp06": 10.0, "cellTemp07": 10.0, "cellTemp08": 10.0, "cellTemp09": 9.0, "cellTemp10": 10.0, "cellTemp11": 10.0, "cellTemp12": 10.0, "cellVoltage01": 4.02, "cellVoltage02": 4.02, "cellVoltage03": 4.02, "cellVoltage04": 4.02, "cellVoltage05": 4.02, "cellVoltage06": 4.02, "cellVoltage07": 4.02, "cellVoltage08": 4.02, "cellVoltage09": 4.02, "cellVoltage10": 4.02, "cellVoltage11": 4.02, "cellVoltage12": 4.02, "cellVoltage13": 4.02, "cellVoltage14": 4.02, "cellVoltage15": 4.02, "cellVoltage16": 4.02, "cellVoltage17": 4.02, "cellVoltage18": 4.02, "cellVoltage19": 4.02, "cellVoltage20": 4.02, "cellVoltage21": 4.02, "cellVoltage22": 4.02, "cellVoltage23": 4.02, "cellVoltage24": 4.02, "cellVoltage25": 4.02, "cellVoltage26": 4.02, "cellVoltage27": 4.02, "cellVoltage28": 4.02, "cellVoltage29": 4.02, "cellVoltage30": 4.02, "cellVoltage31": 4.02, "cellVoltage32": 4.02, "cellVoltage33": 4.02, "cellVoltage34": 4.02, "cellVoltage35": 4.02, "cellVoltage36": 4.02, "cellVoltage37": 4.02, "cellVoltage38": 4.02, "cellVoltage39": 4.02, "cellVoltage40": 4.02, "cellVoltage41": 4.02, "cellVoltage42": 4.02, "cellVoltage43": 4.02, "cellVoltage44": 4.02, "cellVoltage45": 4.02, "cellVoltage46": 4.02, "cellVoltage47": 4.02, "cellVoltage48": 4.02, "cellVoltage49": 4.02, "cellVoltage50": 4.02, "cellVoltage51": 4.02, "cellVoltage52": 4.02, "cellVoltage53": 4.02, "cellVoltage54": 4.02, "cellVoltage55": 4.02, "cellVoltage56": 4.02, "cellVoltage57": 4.02, "cellVoltage58": 4.02, "cellVoltage59": 4.02, "cellVoltage60": 4.02, "cellVoltage61": 4.02, "cellVoltage62": 4.02, "cellVoltage63": 4.02, "cellVoltage64": 4.02, "cellVoltage65": 4.02, "cellVoltage66": 4.02, "cellVoltage67": 4.02, "cellVoltage68": 4.02, "cellVoltage69": 4.02, "cellVoltage70": 4.02, "cellVoltage71": 4.02, "cellVoltage72": 4.02, "cellVoltage73": 4.02, "cellVoltage74": 4.02, "cellVoltage75": 4.02, "cellVoltage76": 4.02, "cellVoltage77": 4.02, "cellVoltage78": 4.02, "cellVoltage79": 4.02, "cellVoltage80": 4.02, "cellVoltage81": 4.02, "cellVoltage82": 4.02, "cellVoltage83": 4.02, "cellVoltage84": 4.02, "cellVoltage85": 4.02, "cellVoltage86": 4.02, "cellVoltage87": 4.02, "cellVoltage88": 4.02, "cellVoltage89": 4.02, "cellVoltage90": 4.02, "cellVoltage91": 4.02, "cellVoltage92": 4.02, "cellVoltage93": 4.02, "cellVoltage94": 4.02, "cellVoltage95": 4.02, "cellVoltage96": 4.02, "gdop": 1.65, "pdop": 1.22, "hdop": 0.95, "vdop": 0.76, "tdop": 0.68, "altitude": 15.1, "gps_device": "/dev/ttyAMA0", "startupThreshold": 12.959999999999999, "shutdownThreshold": 12.6, "emergencyThreshold": 11.76}

    print("running")
    i = 0
    while True:
        car.callback(data)
        sleep(1)
