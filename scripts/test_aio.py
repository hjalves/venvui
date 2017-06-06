# -*- coding: utf-8 -*-

import asyncio
import subprocess
from functools import partial


class SubProcessController:
    def __init__(self, stdout_cb, stderr_cb):
        self.stdout_cb = stdout_cb
        self.stderr_cb = stderr_cb

    async def _consume_stream(self, stream, cb):
        async for line in stream:
            cb(line)

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

async def main():
    sub = SubProcessController(stdout_cb=partial(print, 'stdout:'),
                               stderr_cb=partial(print, 'stderr:'))

    # returncode = await sub.execute('/opt/python36/bin/python3',
    #                                '-mvenv', 'junk/testvenv')
    # returncode = await sub.execute('junk/testvenv/bin/pip',
    #                                'install', '-r', 'requirements.txt')
    # returncode = await sub.execute('junk/testvenv/bin/pip', 'freeze')

    proc = await sub.start('ping', '-c10', '127.0.0.1')
    loop.call_later(5, proc.terminate)
    await proc.wait()



loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
