""" Python interface for EVNotify API """

import aiohttp


class CommunicationError(Exception):
    pass


class RateLimit(Exception):
    pass


class EVNotify:

    def __init__(self, akey=None, token=None):
        self._rest_url = 'https://app.evnotify.de/'
        self._session = aiohttp.ClientSession()
        self._session.headers.update({'User-Agent': 'PyEVNotifyApi/2'})
        self._akey = akey
        self._token = token
        self._timeout = 5

    async def sendRequest(self, method, fnc, useAuthentication=False, data={}):
        params = {**data}

        if useAuthentication:
            params['akey'] = self._akey
            params['token'] = self._token

        try:
            if method == 'get':
                result = await getattr(self._session, method)(self._rest_url + fnc,
                                                              params=params,
                                                              timeout=self._timeout)
            else:
                result = await getattr(self._session, method)(self._rest_url + fnc,
                                                              json=params,
                                                              timeout=self._timeout)
            if result.status_code == 429:
                raise RateLimit(f'code({result.status_code}) test({result.text})')
            elif result.status_code >= 400:
                raise CommunicationError(f'code({result.status_code}) text({result.text})')

            return result.json()

        except aiohttp.ClientConnectionError:
            raise CommunicationError("connection failed")
        #except requests.exceptions.Timeout:
        #    raise CommunicationError("timeout")

    async def getKey(self):
        ret = await self.sendRequest('get', 'key')

        if 'akey' not in ret:
            raise CommunicationError("return akey missing")

        return ret['akey']

    def getToken(self):
        return self._token

    async def register(self, akey, password):
        ret = await self.sendRequest('post', 'register', False, {
            "akey": akey,
            "password": password
        })

        if 'token' not in ret:
            raise CommunicationError("return token missing")

        self._token = ret['token']
        self._akey = akey

    async def login(self, akey, password):
        ret = await self.sendRequest('post', 'login', False, {
            "akey": akey,
            "password": password
        })

        if 'token' not in ret:
            raise CommunicationError("return token missing")

        self._token = ['token']
        self._akey = akey

    async def changePassword(self, oldpassword, newpassword):
        ret = await self.sendRequest('post', 'changepw', True, {
            "oldpassword": oldpassword,
            "newpassword": newpassword
        })

        return ret['changed'] if 'changed' in ret else None

    async def getSettings(self):
        ret = await self.sendRequest('get', 'settings', True)

        if 'settings' not in ret:
            raise CommunicationError("return settings missing")

        return ret['settings']

    async def setSettings(self, settings):
        ret = await self.sendRequest('put', 'settings', True, {
            "settings": settings
        })

        if 'settings' not in ret:
            raise CommunicationError()

    async def setSOC(self, display, bms):
        ret = await self.sendRequest('post', 'soc', True, {
            "display": display,
            "bms": bms
        })

        if 'synced' not in ret:
            raise CommunicationError("return settings missing")

    async def getSOC(self):
        return await self.sendRequest('get', 'soc', True)

    async def setExtended(self, obj):
        ret = await self.sendRequest('post', 'extended', True, obj)

        if 'synced' not in ret:
            raise CommunicationError("return synced missing")

    async def getExtended(self):
        return await self.sendRequest('get', 'extended', True)

    async def getLocation(self):
        return await self.sendRequest('get', 'location', True)

    async def setLocation(self, obj):
        ret = await self.sendRequest('post', 'location', True, obj)

        if 'synced' not in ret:
            raise CommunicationError("return synced missing")

    async def renewToken(self, password):
        ret = await self.sendRequest('put', 'renewtoken', True, {
            "password": password
        })

        if 'token' not in ret:
            raise CommunicationError("return token missing")

        self._token = ret['token']

        return self._token

    async def sendNotification(self, abort=False):
        ret = await self.sendRequest('post', 'notification', True, {
            "abort": abort
        })

        if 'notified' not in ret:
            raise CommunicationError("return notified missing")

        return ret['notified']
