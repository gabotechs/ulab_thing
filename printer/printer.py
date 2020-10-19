import json
import os
import asyncio
import aiofiles
import aiohttp
from typing import Dict, Union

from lib.Logger import get as log
from exceptions import HttpException
from ackWebsockets import SocketMessageResponse
from lib.args import get_args
from printer.printerReceiver import PrinterReceiver


class Printer(PrinterReceiver):
    async def start(self) -> SocketMessageResponse:
        log().info("starting transmission")
        self.transmitting = True
        return SocketMessageResponse(0, "ok")

    async def stop(self) -> SocketMessageResponse:
        log().info("stopping transmission")
        self.transmitting = False
        return SocketMessageResponse(0, "ok")

    async def home(self) -> SocketMessageResponse:
        log().info("homing...")
        await self.octoapi.post_command("G28")
        return SocketMessageResponse(0, "ok")

    async def _print_file(self, gcode: str) -> None:
        log().info("printing file " + gcode + '...')
        if "init_gcode" in self.actualState['settings']:
            for pre_cmd in self.actualState['settings']["init_gcode"].split(";"):
                if len(pre_cmd) < 2:
                    continue
                log().info("executing init gcode " + pre_cmd)
                await self.octoapi.post_command(pre_cmd)
        await self.octoapi.print(gcode.split('/')[-1])

    async def _download_file(self, r: aiohttp.ClientResponse, gcode: str) -> None:
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

    async def print(self, data: Dict[str, str]) -> SocketMessageResponse:
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

            async def download_and_print():
                self.actualState["download"]["file"] = data['file']
                self.actualState["download"]["completion"] = 0.0
                r = await self.ulabapi.download(data['file'])

                if not r.status == 200:
                    log().warning("error downloading file " + data['file'] + " from url: " + str(r.status))
                    self.actualState["download"]["file"] = None
                    self.actualState["download"]["completion"] = -1
                    return SocketMessageResponse(1, "file was not on pandora, and there was an error downloading it")

                await self._download_file(r, gcode)
                await self._print_file(gcode)

            asyncio.get_running_loop().create_task(download_and_print())  # todo: get running loop from somewhere cleaner
            return SocketMessageResponse(0, "file was not on ucloud, downloading it and printing it...")

        await self._print_file(gcode)
        return SocketMessageResponse(0, "ok")

    async def cancel(self) -> SocketMessageResponse:
        log().info("cancelling print...")
        if not self.actualState["status"]["state"]['flags']['printing']:
            return SocketMessageResponse(1, "pandora is not in an printing state")

        await self.octoapi.cancel()
        await self.octoapi.post_command("G1 Z140")
        return SocketMessageResponse(0, "ok")

    async def settings(self, data: Dict[str, str]) -> SocketMessageResponse:
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
        return SocketMessageResponse(0, "ok")

    async def move(self, data: Dict[str, str]) -> SocketMessageResponse:
        log().info("moving...")
        for k in ['axis', 'distance']:
            if k not in data:
                return SocketMessageResponse(1, k + " not specified")

        for cmd in ['G91', 'G1 {}{} F1000'.format(data['axis'], data['distance']), 'G90']:
            log().info("executing command from move command chain " + cmd + "...")
            await self.octoapi.post_command(cmd)
        return SocketMessageResponse(0, "ok")

    async def command(self, data: Dict[str, str]) -> SocketMessageResponse:
        log().info("executing command...")
        if 'command' not in data:
            log().warning("command not specified")
            return SocketMessageResponse(1, "command not specified")

        for cmd in data['command'].split(";"):
            log().info(cmd)
            await self.octoapi.post_command(cmd)
        return SocketMessageResponse(0, "ok")

    async def load(self) -> SocketMessageResponse:
        log().info("loading filament...")
        for cmd in ['M109 S210', 'G92 E0', 'G1 E100 F150', 'M109 S0']:
            log().info("executing command from load command chain " + cmd + "...")
            await self.octoapi.post_command(cmd)
        return SocketMessageResponse(0, "ok")

    async def unload(self) -> SocketMessageResponse:
        log().info("unloading filament...")
        for cmd in ['M109 S210', 'G28', 'G1 Z140', 'G92 E0', 'G1 E15 F150', 'G1 E-135 F300', 'M109 S0']:
            log().info("executing command from unload command chain " + cmd + "...")
            await self.octoapi.post_command(cmd)
        return SocketMessageResponse(0, "ok")

    async def wifi(self, data: Dict[str, str]) -> SocketMessageResponse:
        log().info("changing wifi...")
        for k in ['ssid', 'psk']:
            if k not in data:
                return SocketMessageResponse(1, k + " parameter not specified")

        log().info("new wifi data: ssid=" + data['ssid'] + " psk=" + data['psk'])
        wifi = 'network={\n  ssid="' + data['ssid'] + '"\n  psk="' + data['psk'] + '"\n}\n'
        wpa_supplicant_txt = open("/boot/octopi-wpa-supplicant.txt").read()
        open("/boot/octopi-wpa-supplicant.txt", "w").write(wifi + wpa_supplicant_txt)
        return SocketMessageResponse(0, "ok")

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
            if instruction == "start":
                return await self.start()

            elif instruction == "stop":
                return await self.stop()

            if instruction == 'home':
                return await self.home()

            elif instruction == 'print':
                return await self.print(data)

            elif instruction == 'cancel':
                return await self.cancel()

            elif instruction == 'settings':
                return await self.settings(data)

            elif instruction == 'move':
                return await self.move(data)

            elif instruction == 'command':
                return await self.command(data)

            elif instruction == 'load':
                return await self.load()

            elif instruction == 'unload':
                return await self.unload()

            elif instruction == 'wifi':
                return await self.wifi(data)

            else:
                return SocketMessageResponse(1, data['instruction'] + " instruction not supported")

        except HttpException as e:
            log().warning("octoapi responded " + str(e.code) + ", to " + json.dumps(data))
            return SocketMessageResponse(1, "printer responded " + str(e.code))

        except Exception as e:
            log().error(str(e))
            return SocketMessageResponse(1, str(e))
