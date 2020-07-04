import json
from typing import Dict

import aiohttp
import yaml

from lib.args import get_args
from exceptions import HttpException


class OctoApi:
    def __init__(self, url, config_path):
        self.config_path = config_path
        self.url = url
        self.key = yaml.load(open(self.config_path), Loader=yaml.loader.Loader)['api']['key']
        self.session = aiohttp.ClientSession(headers={"X-Api-Key": self.key, "Content-Type": "application/json"})

    async def connect(self) -> None:
        r = await self.session.post(self.url+'/connection', data=json.dumps({"command": "connect"}))
        if not r.status == 200:
            raise HttpException(r.status)

    async def get_status(self) -> dict:
        r = await self.session.get(self.url+'/printer')
        if not r.status == 200:
            raise HttpException(r.status)
        status = await r.json()
        return status

    async def get_job(self) -> dict:
        r = await self.session.get(self.url+'/job')
        if not r.status == 200:
            raise HttpException(r.status)
        status = await r.json()
        return status

    async def post_command(self, command: str) -> None:
        r = await self.session.post(self.url+'/printer/command', data=json.dumps({"commands": [command]}))
        if not r.status == 204:
            raise HttpException(r.status)

    async def print(self, file: str) -> None:
        r = await self.session.post(self.url+'/files/local/'+file, data=json.dumps({"command": "select", "print": True}))
        if not r.status == 204:
            raise HttpException(r.status)

    async def cancel(self) -> None:
        r = await self.session.post(self.url+'/job', data=json.dumps({"command": "cancel"}))
        if not r.status == 204:
            raise HttpException(r.status)


if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    args = get_args()
    octoapi = OctoApi(args.octoprint_url, args.octoprint_path)
    loop.run_until_complete(octoapi.get_status())

