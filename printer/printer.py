import copy
import json
import os
import asyncio
import time
import aiofiles
from typing import Dict, Any, Union

from aiohttp.client_exceptions import ClientConnectorError

from lib.Logger import get as log
from lib.diffengine import DiffEngine
from exceptions import HttpException
from ackWebsockets import SocketMessageResponse
from lib.args import get_args
from printer.octoapi import OctoApi
from printer.ulabapi import UlabApi


class Printer:
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

        async def unauthorized(data: str = ""):
            log().error("socket unauthorized, code execution blocked, replace the token and restart the system")
            self.connected = False
            while True:
                time.sleep(10)
        self.ulabapi.on_unauthorized = unauthorized

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
            if time.time() - last_connection_try > 20 and (self.actualState["status"]["state"]['text'] == 'Closed' or self.actualState["error"] == 409):
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

    async def listener(self, data_raw: str) -> SocketMessageResponse:
        try:
            data: Dict[str, Union[str, int, float]] = json.loads(data_raw)
        except json.JSONDecodeError:
            log().error("error decoding instruction " + data_raw)
            return SocketMessageResponse(1, "cannot decode instruction")

        if 'instruction' not in data:
            log().warning("received instruction without specifying an instruction name")
            return SocketMessageResponse(1, "instruction not specified")

        instruction = data['instruction']
        log().info("instruction " + instruction + " detected")
        if instruction in ["home", "start", "stop", "print", "command", "load", "unload", "move"]:
            error_flag = False
            try:
                if self.actualState["status"]["state"]['text'] != 'Operational':
                    error_flag = True
            except KeyError:
                error_flag = True
            except TypeError:
                error_flag = True
            if error_flag:
                log().warning("instruction not allowed if pandora is not on an operational state")
                return SocketMessageResponse(1, "printer is not on an operational state")

        try:
            ###### START ######
            if instruction == "start":
                log().info("starting transmission")
                self.transmitting = True
                return SocketMessageResponse(0, "ok")

            ###### STOP ######
            elif instruction == "stop":
                log().info("stopping transmission")
                self.transmitting = False
                return SocketMessageResponse(0, "ok")

            ###### HOME ######
            if instruction == 'home':
                log().info("homing...")
                await self.octoapi.post_command("G28")
                return SocketMessageResponse(0, "ok")

            ###### PRINT ######
            elif instruction == 'print':
                log().info("printing...")
                if 'file' not in data:
                    return SocketMessageResponse(1, "file not specified")

                if self.actualState['download']['file'] is not None:
                    return SocketMessageResponse(1, "file " + self.actualState['download']['file'] + " has already been sheduled to download and print")

                if not self.actualState["status"]["state"]['text'] == 'Operational':
                    return SocketMessageResponse(1, "pandora is not in an operational state")

                upload_path = get_args().octoprint_upload_path
                if not os.path.isdir(upload_path):
                    os.mkdir(upload_path)
                gcode = upload_path + '/' + (data['file'] if data['file'].endswith('.gcode') else data['file'] + '.gcode')
                if not os.path.isfile(gcode):
                    log().info("file " + gcode + " not found, downloading it...")

                    r = await self.ulabapi.download(data['file'])

                    if not r.status == 200:
                        log().warning("error downloading file " + data['file'] + " from url: " + str(r.status))
                        return SocketMessageResponse(1, "file was not on pandora, and there was an error downloading it")

                    self.actualState["download"]["file"] = data['file']
                    self.actualState["download"]["completion"] = 0.0

                    async def download_and_print():
                        f = await aiofiles.open(gcode, mode='wb')
                        readed = 0
                        while True:
                            if r.content_length:
                                self.actualState["download"]["completion"] = readed / r.content_length
                            chunk = await r.content.read(1024)
                            if not chunk:
                                break
                            await f.write(chunk)
                            readed += 1024
                        log().info("file " + gcode + ' downloaded successfully, printing it...')
                        self.actualState["download"]["file"] = None
                        self.actualState["download"]["completion"] = -1
                        await self.syncWithUlab()
                        log().info("printing file " + data['file'] + '...')
                        if "init_gcode" in self.actualState['settings']:
                            for pre_cmd in self.actualState['settings']["init_gcode"].split(";"):
                                if len(pre_cmd) < 2:
                                    continue
                                log().info("executing init gcode " + pre_cmd)
                                await self.octoapi.post_command(pre_cmd)
                        await self.octoapi.print(gcode.split('/')[-1])

                    asyncio.get_running_loop().create_task(download_and_print())  # todo: get running loop from somewhere cleaner
                    return SocketMessageResponse(0, "file was not on ucloud, downloading it and printing it...")

                log().info("printing file " + data['file'] + '...')
                if "init_gcode" in self.actualState['settings']:
                    for pre_cmd in self.actualState['settings']["init_gcode"].split(";"):
                        if len(pre_cmd) < 2:
                            continue
                        log().info("executing init gcode " + pre_cmd)
                        await self.octoapi.post_command(pre_cmd)
                await self.octoapi.print(gcode.split('/')[-1])
                return SocketMessageResponse(0, "ok")

            ###### CANCEL ######
            elif instruction == 'cancel':
                log().info("cancelling print...")
                if not self.actualState["status"]["state"]['flags']['printing']:
                    return SocketMessageResponse(1, "pandora is not in an printing state")

                await self.octoapi.cancel()
                await self.octoapi.post_command("G1 Z140")
                return SocketMessageResponse(0, "ok")

            ###### SETTINGS ######
            elif instruction == 'settings':
                log().info("changing settings...")
                keys = [x for x in data if x not in ['instruction']]
                if not len(keys):
                    return SocketMessageResponse(1, "no new settings has been sent")

                for k in keys:
                    if k not in self.actualState['settings']:
                        return SocketMessageResponse(1, "setting " + k + " not supported")

                for k in keys:
                    self.actualState['settings'][k] = data[k]
                json.dump(self.actualState['settings'], open("../store.json", "w"))
                await self.syncWithUlab()

            ###### MOVE ######
            elif instruction == 'move':
                log().info("moving...")
                for k in ['axis', 'distance']:
                    if k not in data:
                        return SocketMessageResponse(1, k + " not specified")

                for cmd in ['G91', 'G1 {}{} F1000'.format(data['axis'], data['distance']), 'G90']:
                    log().info("executing command from move command chain " + cmd + "...")
                    await self.octoapi.post_command(cmd)
                return SocketMessageResponse(0, "ok")

            ###### COMMAND ######
            elif instruction == 'command':
                log().info("executing command...")
                if 'command' not in data:
                    log().warning("command not specified")
                    return SocketMessageResponse(1, "command not specified")

                for cmd in data['command'].split(";"):
                    log().info(cmd)
                    await self.octoapi.post_command(cmd)
                return SocketMessageResponse(0, "ok")

            ###### LOAD ######
            elif instruction == 'load':
                log().info("loading filament...")
                for cmd in ['M109 S210', 'G92 E0', 'G1 E100 F150', 'M109 S0']:
                    log().info("executing command from load command chain " + cmd + "...")
                    await self.octoapi.post_command(cmd)
                return SocketMessageResponse(0, "ok")

            ###### UNLOAD ######
            elif instruction == 'unload':
                log().info("unloading filament...")
                for cmd in ['M109 S210', 'G28', 'G1 Z140', 'G92 E0', 'G1 E15 F150', 'G1 E-135 F300', 'M109 S0']:
                    log().info("executing command from unload command chain " + cmd + "...")
                    await self.octoapi.post_command(cmd)
                return SocketMessageResponse(0, "ok")

            ###### WIFI ######
            elif instruction == 'wifi':
                log().info("changing wifi...")
                for k in ['ssid', 'psk']:
                    if k not in data:
                        return SocketMessageResponse(1, k + " parameter not specified")

                log().info("new wifi data: ssid=" + data['ssid'] + " psk=" + data['psk'])
                wifi = 'network={\n  ssid="' + data['ssid'] + '"\n  psk="' + data['psk'] + '"\n}\n'
                wpa_supplicant_txt = open("/boot/octopi-wpa-supplicant.txt").read()
                open("/boot/octopi-wpa-supplicant.txt", "w").write(wifi + wpa_supplicant_txt)
                return SocketMessageResponse(0, "ok")

            else:
                return SocketMessageResponse(1, data['instruction'] + " instruction not supported")

        except HttpException as e:
            log().warning("octoapi responded " + str(e.code) + ", to " + json.dumps(data))
            return SocketMessageResponse(1, "printer responded " + str(e.code))

        except Exception as e:
            log().error(str(e))
            return SocketMessageResponse(1, str(e))
