import logging

import coloredlogs

log = None


def get() -> logging.Logger:
    global log
    if not log:
        log = logging.getLogger("main")
        coloredlogs.install(level='DEBUG', logger=log)
        log.propagate = False

    return log
