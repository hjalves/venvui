# -*- coding: utf-8 -*-

import asyncio
from asyncio import subprocess


class SubProcessController:
    def __init__(self, stdout_cb, stderr_cb):
        self.stdout_cb = stdout_cb
        self.stderr_cb = stderr_cb

    async def _consume_stream(self, stream, cb):
        async for line in stream:
            cb(line.decode('utf-8', 'ignore'))

    def _stream_consumed(self, future):
        future.result()

    async def start(self, *args, **kwargs):
        pipe = subprocess.PIPE
        proc = await asyncio.create_subprocess_exec(
            *args, stdin=None, stdout=pipe, stderr=pipe, **kwargs)
        out = self._consume_stream(proc.stdout, self.stdout_cb)
        err = self._consume_stream(proc.stderr, self.stderr_cb)
        # should this be awaited?
        asyncio.gather(out, err).add_done_callback(self._stream_consumed)
        return proc

    async def execute(self, *args, **kwargs):
        process = await self.start(*args, **kwargs)
        return await process.wait()
