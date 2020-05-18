import os
import time
from Logger import get as log
from args import get_args
from printer import Printer

if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    args = get_args()

    async def main():
        if not os.path.isfile(args.ulab_token_path):
            log().error("token file "+args.ulab_token_path+" does not exists, create it with the ulab token inside and restart the system")
            while True:
                time.sleep(10)
        ulab_token = open(args.ulab_token_path).read().replace('\n', "").replace(" ", "")
        printer = Printer(args.octoprint_url, args.octoprint_path, args.ulab_url, ulab_token)
        while True:
            try:
                await printer.ulabapi.connect()
                break
            except Exception as e:
                log().warning("could not connect to ulab, retrying...")
                await asyncio.sleep(1)

        while True:
            await asyncio.sleep(1)
            await printer.updateActualState()
            await printer.syncWithUlab()

    loop.run_until_complete(main())
