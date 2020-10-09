import os
import asyncio
import time
from lib.Logger import get as log
from lib.args import get_args
from printer.ulabapi import UlabApi
from printer.octoapi import OctoApi
from printer.printer import Printer


async def main(loop: asyncio.AbstractEventLoop):
    if not os.path.isfile(args.ulab_token_path):
        log().error(
            "token file " + args.ulab_token_path + " does not exists, create it with the ulab token inside and restart the system")
        while True:
            time.sleep(10)
    ulab_token = open(args.ulab_token_path).read().replace('\n', "").replace(" ", "")
    octoapi = OctoApi(args.octoprint_url, args.octoprint_config_path)
    ulabapi = UlabApi(args.ulab_socket_url, args.ulab_backend_url, ulab_token)
    printer = Printer(octoapi, ulabapi)
    await printer.ulabapi.connect(loop)
    await printer.loop()

if __name__ == '__main__':

    main_loop = asyncio.get_event_loop()
    args = get_args()
    main_loop.run_until_complete(main(main_loop))
