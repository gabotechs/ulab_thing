import json
import os
from typing import Dict, Union

import aiofiles

from Logger import get as log
from args import get_args
# from printer import Printer
from exceptions import HttpException, GetFileException


async def listener(printer, data: Dict[str, Union[str, int, float]]) -> None:
    if 'id' not in data:
        log().warning("received instruction without id, ignoring it")
    if 'instruction' not in data:
        log().warning("received instruction without specifying an instruction")
        printer.ulabapi.socket.emit(data['id'], {"status": 1, "message": "instruction not specified"}, namespace='/pandora')

    instruction = data['instruction']
    log().info("instruction " + instruction + " detected")
    answer_flag = True
    try:
        ###### HOME ######
        if instruction == 'home':
            log().info("homing...")
            await printer.octoapi.post_command("G28")

        ###### PRINT ######
        elif instruction == 'print':
            log().info("printing...")
            if 'file' not in data:
                log().warning("file not specified")
                await printer.ulabapi.socket.emit(data['id'], {"status": 1, "message": "file not specified"}, namespace='/pandora')
                return

            if printer.actualState['download']['file'] is not None:
                log().warning("file " + printer.actualState['download']['file'] + " has already been sheduled to download and print")
                await printer.ulabapi.socket.emit(data['id'], {"status": 1, "message": "file " + printer.actualState['download']['file'] + " has already been sheduled to download and print"}, namespace='/pandora')
                return

            if not printer.actualState["status"]["state"]['text'] == 'Operational':
                log().warning("pandora is not in an operational state")
                await printer.ulabapi.socket.emit(data['id'], {"status": 1, "message": "pandora is not in an operational state"}, namespace='/pandora')
                return

            gcode = get_args().octoprint_path+'/uploads/'+data['file'] if data['file'].endswith('.gcode') else data['file']+'.gcode'
            if not os.path.isfile(gcode):
                log().info("file "+gcode+" not found, downloading it...")

                url = get_args().ulab_url + '/gcodes/' + data['file']
                r = await printer.ulabapi.session.get(url)

                if not r.status == 200:
                    log().warning("error downloading file "+data['file']+" from url:"+str(r.status))
                    await printer.ulabapi.socket.emit(data['id'], {"status": 1, "message": "file was not on pandora, and there was an error downloading it"}, namespace='/pandora')
                    return
                printer.actualState["download"]["file"] = data['file']
                printer.actualState["download"]["completion"] = 0.0
                await printer.ulabapi.socket.emit(data['id'], {"status": 0, "message": "file was not on pandora, downloading it and printing it..."}, namespace='/pandora')
                answer_flag = False
                f = await aiofiles.open(gcode, mode='wb')
                readed = 0
                while True:
                    if r.content_length:
                        printer.actualState["download"]["completion"] = readed / r.content_length
                    chunk = await r.content.read(1024)
                    if not chunk:
                        break
                    await f.write(chunk)
                    readed += 1024
                log().info("file "+data['file']+' downloaded successfully, printing it...')
                printer.actualState["download"]["file"] = None
                printer.actualState["download"]["completion"] = -1
                await printer.syncWithUlab()

            log().info("printing file "+data['file']+'...')
            await printer.octoapi.print(gcode.split('/')[-1])
            await printer.ulabapi.socket.emit("print", {"id": data['file']}, namespace='/pandora')

        ###### CANCEL ######
        elif instruction == 'cancel':
            log().info("cancelling print...")
            if not printer.actualState["status"]["state"]['flags']['printing']:
                log().warning("pandora is not in an printing state")
                await printer.ulabapi.socket.emit(data['id'], {"status": 1, "message": "pandora is not in an printing state"}, namespace='/pandora')
                return

            await printer.octoapi.cancel()
            await printer.octoapi.post_command("G1 Z140")

        ###### SETTINGS ######
        elif instruction == 'settings':
            log().info("changing settings...")
            keys = [x for x in data if x not in ['id', 'instruction']]
            if not len(keys):
                log().warning("no settings has been sent, available settings are " + str([s for s in printer.actualState['settings']]))
                await printer.ulabapi.socket.emit(data['id'], {"status": 1, "message": "no new settings has been sent"}, namespace='/pandora')
                return
            for k in keys:
                if k not in printer.actualState['settings']:
                    log().warning("setting " + k +" not supported, available settings are " + str([s for s in printer.actualState['settings']]))
                    await printer.ulabapi.socket.emit(data['id'], {"status": 1, "message": "setting " + k + " not supported"}, namespace='/pandora')
                    return
            for k in keys:
                printer.actualState['settings'][k] = data[k]
            json.dump(printer.actualState['settings'], open("store.json", "w"))
            await printer.syncWithUlab()

        ###### MOVE ######
        elif instruction == 'move':
            log().info("moving...")
            for k in ['axis', 'distance']:
                if k not in data:
                    log().warning(k+" not specified")
                    await printer.ulabapi.socket.emit(data['id'], {"status": 1, "message": k + " not specified"}, namespace='/pandora')
                    return
            for cmd in ['G91', 'G1 {}{} F1000'.format(data['axis'], data['distance']), 'G90']:
                log().info("executing command from move command chain "+cmd+"...")
                await printer.octoapi.post_command(cmd)

        ###### COMMAND ######
        elif instruction == 'command':
            log().info("executing command...")
            if 'command' not in data:
                log().warning("command not specified")
                await printer.ulabapi.socket.emit(data['id'], {"status": 1, "message": "command not specified"}, namespace='/pandora')
                return
            log().info(data['command'])
            await printer.octoapi.post_command(data['command'])

        ###### LOAD ######
        elif instruction == 'load':
            log().info("loading filament...")
            for cmd in ['M109 S210', 'G92 E0', 'G1 E100 F150', 'M109 S0']:
                log().info("executing command from load command chain "+cmd+"...")
                await printer.octoapi.post_command(cmd)

        ###### UNLOAD ######
        elif instruction == 'unload':
            log().info("unloading filament...")
            for cmd in ['M109 S210', 'G28', 'G1 Z140', 'G92 E0', 'G1 E15 F150', 'G1 E-135 F300', 'M109 S0']:
                log().info("executing command from unload command chain "+cmd+"...")
                await printer.octoapi.post_command(cmd)

        ###### WIFI ######
        elif instruction == 'wifi':
            log().info("changing wifi...")
            for k in ['ssid', 'psk']:
                if k not in data:
                    log().warning(k+" parameter not specified")
                    await printer.ulabapi.socket.emit(data['id'], {"status": 1, "message": k + "parameter not specified"}, namespace='/pandora')
                    return
            log().info("new wifi data: ssid="+data['ssid']+" psk="+data['psk'])
            wifi = 'network={\n  ssid="' + data['ssid'] + '"\n  psk="' + data['psk'] + '"\n}\n'
            wpa_supplicant_txt = open("/boot/octopi-wpa-supplicant.txt").read()
            open("/boot/octopi-wpa-supplicant.txt", "w").write(wifi + wpa_supplicant_txt)

        else:
            log().warning("unsupported instruction " + instruction)
            await printer.ulabapi.socket.emit(data['id'], {"status": 1, "message": data['instruction'] + " instruction not supported"}, namespace='/pandora')
            return

        log().info("instruction "+instruction+" sent correctly")
        if answer_flag:
            await printer.ulabapi.socket.emit(data['id'], {"status": 0, "message": "ok"}, namespace='/pandora')
    except HttpException as e:
        log().warning("octoapi responded " + str(e.code) + ", to " + json.dumps(data))
        if answer_flag:
            await printer.ulabapi.socket.emit(data['id'], {"status": 1, "message": "printer responded " + str(e.code)}, namespace='/pandora')
    except Exception as e:
        log().error(str(e))
        if answer_flag:
            await printer.ulabapi.socket.emit(data['id'], {"status": 1, "message": str(e)}, namespace='/pandora')