import copy
import json
import os
from typing import Dict, Any

from aiohttp.client_exceptions import ClientConnectorError

from Logger import get as log
from diffengine import DiffEngine
from exceptions import HttpException
from listener import listener
from octoapi import OctoApi
from ulabapi import UlabApi


class Printer:
    sentState: Dict[str, Any] = {}
    actualState: Dict[str, Any] = {}

    def __init__(self, octoprint_url, octoprint_config, ulab_url, ulab_token):
        self.octoapi = OctoApi(octoprint_url, octoprint_config)
        self.ulabapi = UlabApi(ulab_url, ulab_token)
        self.diffengine = DiffEngine()

        @self.ulabapi.socket.event(namespace='/pandora')
        async def connect():
            log().info("socket connected, yujuu! :)")
            await self.init()

        @self.ulabapi.socket.event(namespace='/pandora')
        async def disconnect():
            log().info("socket disconnected, oh no! :(")

        @self.ulabapi.socket.event(namespace='/pandora')
        async def init():
            log().info("data initialization requested")
            await self.init()

        @self.ulabapi.socket.event(namespace='/pandora')
        async def instruction(data):
            log().info("incoming instruction:"+json.dumps(data))
            await listener(self, data)

    async def init(self):
        self.sentState = {}
        if os.path.isfile("store.json"):
            self.actualState = {"settings": json.load(open("store.json"))}
        else:
            self.actualState = {"settings": {"init_gcode": "M851 Z-0.5"}}
            json.dump(self.actualState['settings'], open("store.json", "w"))
        self.actualState['download'] = {'file': None, 'completion': -1}

        await self.updateActualState()
        await self.syncWithUlab()

    async def updateSettings(self, spec: Dict):
        for k in spec:
            self.actualState["settings"][k] = spec[k]
        json.dump(self.actualState["settings"], open("store.json", "w"))

    async def updateActualState(self):
        try:
            self.actualState["status"] = await self.octoapi.get_status()
            self.actualState["job"] = await self.octoapi.get_job()
            if self.actualState["status"]["state"]['text'] == 'Closed':
                log().warning("closed status detected, forcing connection...")
                await self.octoapi.connect()

        except HttpException as e:
            self.actualState["status"] = {"state": {"text": "Disconnected"}}
            if e.code == 409:
                log().warning("octoprint returned 409 while requesting status, forcing connection...")
                await self.octoapi.connect()

        except ClientConnectorError as e:
            log().error("error conectando con el servidor de octoprint: "+str(e))
            self.actualState["status"] = {"state": {"text": "Disconnected"}}

    async def syncWithUlab(self):
        spec = self.diffengine.diff(self.actualState, self.sentState)
        if len(spec):
            try:
                await self.ulabapi.update_status(spec)
                self.sentState = copy.deepcopy(self.actualState)
            except Exception as e:
                log().error(e)
