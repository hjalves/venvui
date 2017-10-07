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
        self.services = {}
        self.running = True
        task = asyncio.ensure_future(self.run())
        task.add_done_callback(lambda f: f.result())

    async def run(self):
        while True:
            await self._update_active_bulk()
            await asyncio.sleep(10)

    async def add_service(self, name, project_key):
        logger.debug("Adding service '%s' from '%s'", name, project_key)
        service = await self._get_status(name)
        #if 'error' in service:
        #    raise SystemdException("Error while adding service '%s': %s" %
        #                           (name, service['error']))
        service['project_key'] = project_key
        self.services[name] = service
        return dict(service)

    async def get_status(self, service):
        if service not in self.services:
            raise KeyError("Service '%s' unknown" % service)
        updated = await self._get_status(service)
        # TODO: detect changes
        self.services[service].update(updated)
        return dict(self.services[service])

    def list_services(self, by_project_key=None):
        services = self.services.items()
        if by_project_key:
            services = ((key, props) for key, props in services
                        if props['project_key'] == by_project_key)
        return [dict(name=key, **props)
                for key, props in services]

    async def execute(self, unit, command):
        out, err, code = await self._execute(command, unit)
        out = out.strip() + err.strip()
        if code != 0:
            raise SystemdException("%s (code: %d)" % (out, code))
        return out

    async def _execute(self, *args, **kwargs):
        pipe = subprocess.PIPE
        logger.debug("Executing: systemctl %s", ' '.join(args))
        proc = await asyncio.create_subprocess_exec(
            *self.cmd_prefix, *args, stdin=None, stdout=pipe, stderr=pipe,
            **kwargs)
        out, err = await proc.communicate()
        out = out.decode('utf-8', 'ignore')
        err = err.decode('utf-8', 'ignore')
        logger.debug("Finished with code: %s, out: %r, err: %r",
                     proc.returncode, out, err)
        return out, err, proc.returncode

    async def _get_status(self, service):
        output = {}
        out, err, code = await self._execute('is-enabled', service)
        output['startup'] = 'error' if err else out.strip()
        output['error'] = err.strip() if err else None
        out, err, code = await self._execute('is-active', service)
        output['status'] = out.strip()
        return output

    async def _update_active_bulk(self):
        if not self.services:
            return
        out, err, code = await self._execute('is-active', *self.services)
        status = out.strip().split('\n')
        assert err == '', err
        for service, status in zip(self.services, status):
            # TODO: detect changes
            self.services[service]['status'] = status
