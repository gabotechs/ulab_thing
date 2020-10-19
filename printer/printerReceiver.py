import copy
from abc import ABC, abstractmethod
import json
import os
import asyncio
import time
from typing import Dict, Any

from aiohttp.client_exceptions import ClientConnectorError

from lib.Logger import get as log
from lib.diffengine import DiffEngine
from exceptions import HttpException
from ackWebsockets import SocketMessageResponse
from printer.octoapi import OctoApi
from printer.ulabapi import UlabApi


class PrinterReceiver(ABC):
    sentState: Dict[str, Any] = {}
    actualState: Dict[str, Any] = {}
    connected: bool = False
    transmitting: bool = False

    def __init__(self, octoapi: OctoApi, ulabapi: UlabApi):
        self.octoapi = octoapi
        self.ulabapi = ulabapi
        self.diffengine = DiffEngine()

        async def connect(data: str = ""):
            log().info("socket connected, yujuu! :)")
            self.connected = True

        self.ulabapi.on_connect = connect

        async def disconnect(data: str = ""):
            self.connected = False
            self.transmitting = False
            log().warning("socket disconnected, oh no! :(")
        self.ulabapi.on_disconnect = disconnect

        async def error(e: Exception):
            self.connected = False
            self.transmitting = False
            log().warning("error on Socket: "+str(e))
        self.ulabapi.on_error = error

        async def stop(data: str = ""):
            log().info("socket requested to stop transmission")
            self.transmitting = False

        self.ulabapi.on_stop = stop

        async def init(data: str = ""):
            log().info("data initialization requested, starting transmission")
            await self.init()
            await self.syncWithUlab()
        self.ulabapi.on_init = init

        async def instruction(data: str) -> SocketMessageResponse:
            log().info("incoming instruction: "+data)
            response = await self.listener(data)
            if response.status:
                log().warning(f"response for instruction with status {response.status}: {response.message}")
            return response
        self.ulabapi.on_instruction = instruction

    async def loop(self):
        last_connection_try = 0
        while True:
            await self.updateActualState()
            status = self.actualState["status"]["state"]["text"] if "status" in self.actualState and "state" in self.actualState["status"] and "text" in self.actualState["status"]["state"] else "unknown"
            error = self.actualState["error"] if "error" in self.actualState else 0
            if time.time() - last_connection_try > 20 and (status == 'Closed' or error == 409):
                log().warning("closed status detected, forcing connection...")
                last_connection_try = time.time()
                try:
                    await self.octoapi.connect()
                    log().info(f"printer connected correctly")

                except HttpException:
                    log().warning(f"could not connect printer, trying again in {20}s")

                except ClientConnectorError as e:
                    log().error(f"client connection error with octoprint server while trying to connect printer: "+str(e))

                except Exception as e:
                    log().error(f"unknown error while trying to connect printer: "+str(e))

            if self.connected and self.transmitting:
                await self.syncWithUlab()
            await asyncio.sleep(1)

    async def init(self):
        self.transmitting = True
        self.sentState = {}
        if os.path.isfile("../store.json"):
            self.actualState = {"settings": json.load(open("../store.json"))}
        else:
            self.actualState = {"settings": {"init_gcode": "M851 Z-0.5"}}
            json.dump(self.actualState['settings'], open("../store.json", "w"))
        self.actualState['download'] = {'file': None, 'completion': -1}
        self.actualState['error'] = None

        await self.updateActualState()

    async def updateSettings(self, spec: Dict):
        for k in spec:
            self.actualState["settings"][k] = spec[k]
        json.dump(self.actualState["settings"], open("../store.json", "w"))

    async def updateActualState(self):
        try:
            self.actualState["status"] = await self.octoapi.get_status()
            self.actualState["job"] = await self.octoapi.get_job()
            self.actualState["error"] = None

        except HttpException as e:
            self.actualState["status"] = {"state": {"text": "Disconnected"}}
            self.actualState["error"] = e.code

        except ClientConnectorError as e:
            log().error("error connecting to octoprint server: "+str(e))
            self.actualState["status"] = {"state": {"text": "Disconnected"}}
            self.actualState["error"] = 450

        except Exception as e:
            log().error("unknown error updating status: "+str(e))
            self.actualState["status"] = {"state": {"text": "Disconnected"}}
            self.actualState["error"] = 500

    async def _updateActualState(self):
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

    @abstractmethod
    async def listener(self, data_raw: str) -> SocketMessageResponse:
        pass
