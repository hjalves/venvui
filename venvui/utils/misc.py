# -*- coding: utf-8 -*-

import datetime
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


def json_dumps(obj):
    def default(obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        raise TypeError('%r is not JSON serializable' % obj)
    return json.dumps(obj, default=default)


def jsonify(*a, status=200, reason=None, headers=None, content_type=None,
            dumps=json_dumps, **kw):
    content_type = content_type or 'application/json'
    text = dumps(dict(*a, **kw))
    return web.Response(text=text, status=status, reason=reason,
                        headers=headers, content_type=content_type)
