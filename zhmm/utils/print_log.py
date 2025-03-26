# -*- coding: utf-8 -*-
import log


def info(*args, **kwargs):
    print(*args, **kwargs)
    message = " ".join(map(str, args))
    log.info(message)


def error(*args, **kwargs):
    print(*args, **kwargs)
    message = " ".join(map(str, args))
    log.error(message)


def debug(*args, **kwargs):
    print(*args, **kwargs)
    message = " ".join(map(str, args))
    log.debug(message)


def waring(*args, **kwargs):
    print(*args, **kwargs)
    message = " ".join(map(str, args))
    log.debug(message)