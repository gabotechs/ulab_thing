from Logger import get as log
from args import get_args
from printer import Printer

if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    args = get_args()

    async def main():
        printer = Printer(args.octoprint_url, args.octoprint_path, args.ulab_url, args.ulab_token)
        while True:
            try:
                await printer.ulabapi.connect()
                break
            except Exception as e:
                log().warning("could not connect to ulab, retrying...")
                await asyncio.sleep(1)

        while True:
            await printer.updateActualState()
            await printer.syncWithUlab()
            await asyncio.sleep(1)

    loop.run_until_complete(main())
