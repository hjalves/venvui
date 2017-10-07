# -*- coding: utf-8 -*-

import logging
from asyncio import Event
from datetime import datetime

logger = logging.getLogger(__name__)


class StreamLog:

    def __init__(self):
        self.stream = []
        self.written = Event()
        self.open = True

    def __aiter__(self):
        return self.retrieve()

    def put(self, **data):
        # logger.debug('[%s]: %s', channel, line.replace('\n', ''))
        if not self.open:
            raise EOFError("StreamLog is closed")
        if 'time' not in data:
            data['time'] = datetime.utcnow()
        self.stream.append(dict(**data))
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
