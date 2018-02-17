# -*- coding: utf-8 -*-

import asyncio
import json
import logging
from datetime import datetime

from venvui.utils.streamlog import StreamLog
from venvui.utils.subproc import SubProcessController


logger = logging.getLogger(__name__)


def parse_journal_line(line):
    try:
        line = line.decode('utf-8', 'ignore')
        obj = json.loads(line)
        timestamp = int(obj['__REALTIME_TIMESTAMP']) / 1e6
        message = obj['MESSAGE']
        # message can be a list of bytes (integers between 0 and 255)
        if isinstance(message, list):
            message = bytes(message).decode('utf-8', 'ignore')
        obj = {'time': datetime.utcfromtimestamp(timestamp),
               'from': obj.get('SYSLOG_IDENTIFIER'),
               'message': message,
               'transport': obj.get('_TRANSPORT')}
        return obj
    except json.JSONDecodeError:
        logger.warning('Cannot decode json from stdout line: %s', line)
        return None


class LogViewService:
    def __init__(self):
        pass

    async def get_systemd_log(self, unit, lines):
        command = ('journalctl', '--user', '--follow',  '--output=json',
                   '--unit=' + unit, '--lines=%s' % lines,)
        stream_log = StreamLog()

        def stdout_callback(line):
            obj = parse_journal_line(line)
            if obj:
                stream_log.put(**obj)

        def process_closed(future):
            returncode = future.result()
            logger.debug("Process complete (%s), return code: %s",
                         ' '.join(command), returncode)
            stream_log.close()

        controller = SubProcessController(stdout_callback, None)
        # Start process
        process = await controller.start(*command)
        logger.debug("Process started (%s), pid: %s", ' '.join(command),
                     process.pid)
        # After process is done, closes stream log
        asyncio.ensure_future(process.wait()).add_done_callback(process_closed)

        try:
            # noinspection PyTypeChecker
            async for elem in stream_log.retrieve():
                yield elem
        finally:
            if process.returncode is None:
                process.terminate()
