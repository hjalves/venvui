# -*- coding: utf-8 -*-

import asyncio
from asyncio import subprocess
import logging


logger = logging.getLogger(__name__)


class SystemdException(Exception):
    pass


class SystemdManager:

    def __init__(self):
        self.cmd_prefix = ['systemctl', '--user', '--no-legend']

    async def _execute(self, *args, **kwargs):
        pipe = subprocess.PIPE
        logger.debug("Executing: systemctl... %s", args)
        proc = await asyncio.create_subprocess_exec(
            *self.cmd_prefix, *args, stdin=None, stdout=pipe, stderr=pipe,
            **kwargs)
        out, err = await proc.communicate()
        out = out.decode('utf-8', 'ignore')
        err = err.decode('utf-8', 'ignore')
        logger.debug("Finished with code: %s, out: %r, err: %r",
                     proc.returncode, out, err)
        return out, err, proc.returncode

    async def get_status(self, unit):
        out, err, code = await self._execute('is-enabled', unit)
        if err:
            return {'error': err.strip()}
        enabled = out.strip()
        out, err, code = await self._execute('is-active', unit)
        active = out.strip()
        return {'startup': enabled,
                'status': active}

    async def execute(self, unit, command):
        out, err, code = await self._execute(command, unit)
        out = out.strip() + err.strip()
        if code != 0:
            raise SystemdException("%s (code: %d)" % (out, code))
        return out
