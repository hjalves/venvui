# -*- coding: utf-8 -*-
from venvui.utils.streamlog import StreamLog
from venvui.utils.subproc import SubProcessController


class LogViewService:
    def __init__(self):
        pass

    async def journal_log(self, service, lines=10):
        stream_log = StreamLog()
