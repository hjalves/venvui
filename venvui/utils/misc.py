# -*- coding: utf-8 -*-

import json
import random
import string

from aiohttp import web


def keygen(n=8):
    random.seed(1)
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))


async def save_part_to_file(f, part_reader):
    size = 0
    while True:
        chunk = await part_reader.read_chunk()  # 8192 bytes by default.
        if not chunk:
            break
        size += len(chunk)
        f.write(chunk)
    return size


def json_error(error, status):
    message = {'error': error, 'status': status}
    return web.json_response(message, status=status)
