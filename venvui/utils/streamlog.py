# -*- coding: utf-8 -*-

import logging
from asyncio import Event
from functools import partial
from datetime import datetime

logger = logging.getLogger(__name__)


class StreamLog:

    def __init__(self):
        self.stream = []
        self.written = Event()
        self.subscribers = set()
        self.open = True

    def __aiter__(self):
        return self.retrieve()

    def writer(self, channel=None):
        return partial(self.put, channel=channel)

    def put(self, line, channel=None):
        # logger.debug('[%s]: %s', channel, line.replace('\n', ''))
        if not self.open:
            raise EOFError("StreamLog is closed")
        timestamp = datetime.utcnow()
        line = str(line).replace('\n', '')
        self.stream.append((timestamp, channel, line))
        self.written.set()
        self.written.clear()

    def close(self):
        self.open = False
        self.written.set()

    def retrieve_partial(self):
        return list(self.stream)

    async def retrieve(self):
        for record in self.stream:
            yield record
        while self.open:
            last = len(self.stream)
            await self.written.wait()
            for record in self.stream[last:]:
                yield record
