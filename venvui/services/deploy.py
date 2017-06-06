# -*- coding: utf-8 -*-

import asyncio
import logging
from uuid import uuid4

from venvui.utils.streamlog import StreamLog
from venvui.utils.subproc import SubProcessController

logger = logging.getLogger(__name__)


class Deployment:

    def __init__(self, svc, uuid, project_key, venv_path, pkg):
        self.svc = svc
        self.uuid = uuid
        self.project_key = project_key
        self.venv_path = venv_path
        self.pkg = pkg
        self.state = 'pending'
        self.stream_log = StreamLog()
        self.sub = SubProcessController(self.stream_log.writer('out'),
                                        self.stream_log.writer('err'))
        #self.sub = SubProcessController(self.debug_log, self.debug_log_err)
        logger.info("Deployment '%s' is: %s", self.uuid, self.state)

    def debug_log(self, line):
        logger.debug("proc(out): %s", line.replace('\n', ''))

    def debug_log_err(self, line):
        logger.warning("proc(err): %s", line.replace('\n', ''))

    async def run(self):
        self.state = 'running'
        logger.info("Deployment '%s' is: %s", self.uuid, self.state)
        python_path = '/opt/python36/bin/python3'
        pip_path = self.venv_path / 'bin' / 'pip'
        await self._execute(python_path, '-mvenv', str(self.venv_path))
        await self._execute(str(pip_path), 'install', self.pkg['path'])
        await self._execute('ping', '-c10', '127.0.0.1')
        self.state = 'done'
        logger.info("Deployment '%s' is: %s", self.uuid, self.state)

    def start(self):
        future = asyncio.ensure_future(self.run())
        future.add_done_callback(self._done)

    def _done(self, future):
        future.result()
        self.stream_log.unsubscribe_all()

    async def _execute(self, *command):
        self.stream_log.put('$ ' + ' '.join(command), channel='shell')
        return_code = await self.sub.execute(*command)
        self.stream_log.put('[Process completed with code: %s]' % return_code,
                            channel='shell')

    def subscribe_log(self, callback):
        self.stream_log.subscribe(callback)

    def unsubscribe_log(self, callback):
        self.stream_log.unsubscribe(callback)

    def retrieve_log(self):
        return self.stream_log.retrieve_all()

    def to_dict(self):
        return {
            'uuid': self.uuid,
            'project_key': self.project_key,
            'venv_name': str(self.venv_path.name),
            'pkg_name': self.pkg['pkg_name'],
            'state': self.state
        }


class DeploymentService:

    def __init__(self):
        self.deployments = {}

    def deploy(self, project_key, venv_path, package):
        uuid = str(uuid4())
        self.deployments[uuid] = Deployment(self, uuid, project_key, venv_path,
                                            package)
        self.deployments[uuid].start()
        return self.deployments[uuid]

    def list_deployments(self, by_project_key=None):
        if by_project_key:
            return [deployment for deployment in self.deployments.values()
                    if deployment.project_key == by_project_key]
        return list(self.deployments.values())
