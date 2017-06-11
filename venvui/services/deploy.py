# -*- coding: utf-8 -*-

import asyncio
import logging
import time

from venvui.utils.misc import keygen
from venvui.utils.streamlog import StreamLog
from venvui.utils.subproc import SubProcessController

logger = logging.getLogger(__name__)


class Deployment:

    def __init__(self, svc, key, project_key, venv_path, pkg):
        self.svc = svc
        self.key = key
        self.project_key = project_key
        self.venv_path = venv_path
        self.pkg = pkg
        self.state = 'pending'
        self.stream_log = StreamLog()
        self.sub = SubProcessController(self.stream_log.writer('out'),
                                        self.stream_log.writer('err'))
        logger.info("Deployment '%s' is: %s", self.key, self.state)

    def partial_log(self):
        return self.stream_log.retrieve_partial()

    def log(self):
        return self.stream_log.retrieve()

    async def _run(self):
        self.state = 'running'
        logger.info("Deployment '%s' is: %s", self.key, self.state)
        python_path = '/opt/python36/bin/python3'
        pip_path = self.venv_path / 'bin' / 'pip'
        await self._execute('ping', '-c10', '127.0.0.1')
        await self._execute(python_path, '-mvenv', str(self.venv_path))
        await self._execute(str(pip_path), 'install', self.pkg['path'])
        await self._execute('ping', '-c10', '127.0.0.1')
        self.stream_log.close()
        self.state = 'done'
        logger.info("Deployment '%s' is: %s", self.key, self.state)

    def start(self):
        future = asyncio.ensure_future(self._run())
        future.add_done_callback(self._done)

        debuglog = asyncio.ensure_future(self._debuglog())
        debuglog.add_done_callback(self._done_debuglog)

    def _done(self, future):
        future.result()
        #self.stream_log.unsubscribe_all()

    def _done_debuglog(self, future):
        future.result()
        logger.info("[%s] Debuglog closed!", self.key)

    async def _debuglog(self):
        async for (timestamp, channel, line) in self.stream_log:
            logger.debug('[%s] (%s): %s', self.key, channel, line)

    async def _execute(self, *command):
        now = time.time()
        self.stream_log.put('$ ' + ' '.join(command), channel='shell')
        return_code = await self.sub.execute(*command)
        elapsed = time.time() - now
        self.stream_log.put('[Process completed in %.2f seconds with code: %s]'
                            % (elapsed, return_code), channel='shell')

    def to_dict(self):
        return {
            'key': self.key,
            'project_key': self.project_key,
            'venv_name': str(self.venv_path.name),
            'pkg_name': self.pkg['pkg_name'],
            'state': self.state
        }


class DeploymentService:

    def __init__(self):
        self.deployments = {}

    def deploy(self, project_key, venv_path, package):
        key = keygen()
        self.deployments[key] = Deployment(self, key, project_key, venv_path,
                                            package)
        self.deployments[key].start()
        return self.deployments[key]

    def list_deployments(self, by_project_key=None):
        if by_project_key:
            return [deployment for deployment in self.deployments.values()
                    if deployment.project_key == by_project_key]
        return list(self.deployments.values())

    def get_deployment(self, key):
        return self.deployments[key]
