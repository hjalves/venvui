# -*- coding: utf-8 -*-

import logging
from collections import deque
from functools import partial
from time import time

logger = logging.getLogger(__name__)


class StreamLog:

    def __init__(self):
        self.stream = deque()
        self.subscribers = set()

    def writer(self, channel=None):
        return partial(self.put, channel=channel)

    def put(self, line, channel=None):
        logger.debug('[%s]: %s', channel or 'default', line.replace('\n', ''))
        timestamp = time()
        self.stream.append((timestamp, channel, line))
        self._broadcast(timestamp, line, channel)

    def retrieve_all(self):
        return list(self.stream)

    def _broadcast(self, timestamp, line, channel):
        for callback in self.subscribers:
            callback(timestamp, line, channel)

    def subscribe(self, callback):
        self.subscribers.add(callback)

    def unsubscribe(self, callback):
        self.subscribers.remove(callback)

    def unsubscribe_all(self):
        self.subscribers.clear()
