# -*- coding: utf-8 -*-

import asyncio
import logging
import os
import time
from pathlib import Path

from venvui.utils.misc import keygen
from venvui.utils.streamlog import StreamLog
from venvui.utils.subproc import SubProcessController

logger = logging.getLogger(__name__)


class Deployment:

    current_venv_name = 'current'

    def __init__(self, svc, key, project_key, venv_root, venv_name, pkg):
        self.svc = svc
        self.key = key
        self.project_key = project_key
        self.venv_root = venv_root
        self.venv_name = venv_name
        self.pkg = pkg

        self.venv_path = venv_root / venv_name
        self.symlink_path = venv_root / self.current_venv_name
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
        python_path = '/usr/bin/python3.6'
        #venv_command = ['/opt/python36/bin/python3', '-mvenv']
        create_venv_command = ['/usr/bin/virtualenv', '-p/usr/bin/python3.6']
        pip_path = self.venv_path / 'bin' / 'pip'
        await self._execute('ping', '-c10', '127.0.0.1')
        await self._execute(*create_venv_command, str(self.venv_path))
        await self._execute(str(pip_path), 'install', self.pkg['path'])
        await self._execute('ping', '-c10', '127.0.0.1')
        self.stream_log.close()

    def start(self):
        future = asyncio.ensure_future(self._run())
        future.add_done_callback(self._done)

        debuglog = asyncio.ensure_future(self._debuglog())
        debuglog.add_done_callback(self._done_debuglog)

        writelog = asyncio.ensure_future(self._logfile())
        writelog.add_done_callback(lambda f: f.result())

    def _done(self, future):
        future.result()
        try:
            self.symlink_path.unlink()
        except FileNotFoundError:
            pass
        self.symlink_path.symlink_to(self.venv_name)
        self.state = 'done'
        logger.info("Deployment '%s' is: %s", self.key, self.state)
        #self.stream_log.unsubscribe_all()

    def _done_debuglog(self, future):
        future.result()
        logger.info("[%s] Debuglog closed!", self.key)

    async def _debuglog(self):
        async for (timestamp, channel, line) in self.stream_log:
            logger.debug('[%s] (%s): %s', self.key, channel, line)

    async def _logfile(self):
        filename = 'deployment-%s.log' % self.key
        with open(self.svc.temp_path / filename, 'w') as f:
            async for (tstamp, channel, line) in self.stream_log:
                f.write('%s | %s | %s\n' % (tstamp.isoformat(), channel, line))


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
            'venv_name': self.venv_name,
            'package_filename': self.pkg['filename'],
            'state': self.state
        }


class DeploymentService:

    def __init__(self, temp_path):
        self.deployments = {}
        self.temp_path = Path(temp_path)

    def deploy(self, project_key, venv_root, venv_name, package):
        key = '%s-%s' % (project_key, venv_name)
        self.deployments[key] = Deployment(self, key, project_key, venv_root,
                                           venv_name, package)
        self.deployments[key].start()
        return self.deployments[key]

    def list_deployments(self, by_project_key=None):
        if by_project_key:
            return [deployment for deployment in self.deployments.values()
                    if deployment.project_key == by_project_key]
        return list(self.deployments.values())

    def get_deployment(self, key):
        return self.deployments[key]
