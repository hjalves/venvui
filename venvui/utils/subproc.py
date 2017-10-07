# -*- coding: utf-8 -*-

import asyncio
from asyncio import subprocess


class SubProcessController:
    def __init__(self, stdout_cb, stderr_cb):
        self.stdout_cb = stdout_cb
        self.stderr_cb = stderr_cb

    async def _consume_stream(self, stream, callback):
        async for line in stream:
            if callback:
                callback(line)

    async def start(self, *command, shell=False, **kw):
        pipe = subprocess.PIPE
        func = (asyncio.create_subprocess_shell
                if shell else asyncio.create_subprocess_exec)
        proc = await func(*command, stdin=None, stdout=pipe, stderr=pipe, **kw)
        out = self._consume_stream(proc.stdout, self.stdout_cb)
        err = self._consume_stream(proc.stderr, self.stderr_cb)
        asyncio.gather(out, err).add_done_callback(lambda f: f.result())
        return proc

    async def execute(self, *command, shell=False, **kwargs):
        process = await self.start(*command, shell=shell, **kwargs)
        return await process.wait()
