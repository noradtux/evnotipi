""" Simple web service """
import logging
from asyncio import Condition
from aiohttp import web


class WebService():
    def __init__(self, config, car):
        self._log = logging.getLogger("EVNotiPi/WebService")
        self._log.info("Initializing WebService")

        self._car = car
        self._data = {}
        self._data_available = Condition()
        self._running = False
        self._server = None
        self._runner = None
        self._safe_path = config.get('safe_path', '/var/cache/evnotipi')

        app = web.Application()
        app.add_routes([web.get('/data/live/ws', self._handle_websocket),
                        web.get('/data', self._handle_data),
                        web.post('/layout/store', self._handle_layout_store),
                        web.get('/layout/load', self._handle_layout_load),
                        web.static('/static/', 'web', append_version=True),
                        web.get('/', self._handle_index),
                        ])
        self._app = app

    async def _handle_websocket(self, request):
        ws = web.WebSocketResponse
        await ws.prepare(request)

        while self._running:
            with self._data_available:
                await self._data_available.wait()
                await ws.send_json(self._data)

        return ws

    async def _handle_data(self, request):
        return web.json_response(self._data)

    async def _handle_index(self, request):
        return web.FileResponse('index.html')

    async def _handle_layout_load(self, request):
        return web.FileResponse(f'{self._safe_path}/layout.json')

    async def _handle_layout_store(self, request):
        async with open(self._safe_path + '/layout.json', 'wb') as file:
            await file.write(request.read())
        return "Layout stored"

    async def start(self):
        self._running = True
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._server = web.TCPSite(self._runner, '::', 8080)
        await self._server.start()

        self._car.register_data(self._data_callback)

    async def stop(self):
        self._car.unregister_data(self._data_callback)
        self._running = False
        async with self._data_available:
            self._data_available.notify_all()
        await self._server.stop()
        await self._runner.cleanup()
        self._runner = None
        self._server = None

    async def _data_callback(self, data):
        async with self._data_available:
            self._data = data
            self._data_available.notify_all()

    def check_thread(self):
        return self._running
