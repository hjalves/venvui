# -*- coding: utf-8 -*-

import asyncio
import datetime
import logging
import os
import time
from pathlib import Path

from venvui.utils.misc import keygen, json_dumps
from venvui.utils.streamlog import StreamLog
from venvui.utils.subproc import SubProcessController

logger = logging.getLogger(__name__)


class Deployment:

    def __init__(self, svc, key, project_key, venv_root, venv_name, pkg,
                 callback=None):
        self.svc = svc
        self.key = key
        self.project_key = project_key
        self.venv_root = venv_root
        self.venv_name = venv_name
        self.pkg = pkg
        self.callback = callback

        self.venv_path = venv_root / venv_name
        self.stream_log = StreamLog()
        self.state = 'pending'

        # Timestamps
        self.created_at = datetime.datetime.utcnow()
        self.started_at = None
        self.stopped_at = None

        self.stream_log.put(event='new_deployment',
                            key=self.key,
                            project_key=self.project_key,
                            venv_name=self.venv_name,
                            package_filename=self.pkg['filename'],
                            state=self.state)

        self.sub = SubProcessController(self.stdout_writer, self.stderr_writer)
        logger.info("Deployment '%s' is: %s", self.key, self.state)

    def stdout_writer(self, line):
        line = line.decode('utf-8', 'ignore')
        self.stream_log.put(event='command_output', channel='out', line=line)

    def stderr_writer(self, line):
        line = line.decode('utf-8', 'ignore')
        self.stream_log.put(event='command_output', channel='err', line=line)

    def partial_log(self):
        return self.stream_log.retrieve_partial()

    def log(self):
        return self.stream_log.retrieve()

    async def _run(self):
        self.state = 'running'
        self.started_at = datetime.datetime.utcnow()
        self.stream_log.put(event='state_changed', state=self.state)
        logger.info("Deployment '%s' is: %s", self.key, self.state)
        python_path = '/usr/bin/python3.6'
        create_venv_command = ['/usr/bin/virtualenv', '-p' + python_path]
        pip_path = self.venv_path / 'bin' / 'pip'
        #await self._execute('ping -c10 127.0.0.1', shell=True)
        await self._execute(*create_venv_command, str(self.venv_path))
        ret = await self._execute(str(pip_path), 'install', self.pkg['path'])
        #await self._execute('ping -c1000 127.0.0.1', shell=True)
        return ret == 0

    def start(self):
        future = asyncio.ensure_future(self._run())
        future.add_done_callback(self._done)

        #debuglog = asyncio.ensure_future(self._debuglog())
        #debuglog.add_done_callback(lambda f: f.result())

        logfile = asyncio.ensure_future(self._logfile())
        logfile.add_done_callback(lambda f: f.result())

    def _done(self, future):
        success = future.result()
        self.state = 'done' if success else 'failed'
        self.stopped_at = datetime.datetime.utcnow()
        self.stream_log.put(event='state_changed', state=self.state)
        self.stream_log.close()
        logger.info("Deployment '%s' is: %s", self.key, self.state)
        if self.callback:
            self.callback(self)

    async def _debuglog(self):
        async for event in self.stream_log:
            logger.debug('[%s] %s', self.key, event)

    async def _logfile(self):
        filename = 'deployment-%s.ndjson' % self.key
        with open(self.svc.logs_path / filename, 'w') as f:
            async for event in self.stream_log:
                f.write(json_dumps(event) + '\n')
                f.flush()

    async def _execute(self, *command, shell=False):
        now = time.time()
        log_command = command[0] if len(command) == 1 else command
        self.stream_log.put(event='command_started', command=log_command,
                            shell=shell)
        return_code = await self.sub.execute(*command, shell=shell)
        elapsed = time.time() - now
        self.stream_log.put(event='command_finished', command=log_command,
                            elapsed=elapsed, return_code=return_code)
        return return_code

    def to_dict(self):
        return {
            'key': self.key,
            'project_key': self.project_key,
            'venv_name': self.venv_name,
            'package_filename': self.pkg['filename'],
            'state': self.state,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'stopped_at': self.stopped_at
        }


class DeploymentService:

    def __init__(self, temp_path, logs_path):
        self.deployments = {}
        self.temp_path = Path(temp_path)
        self.logs_path = Path(logs_path)

    def deploy(self, project_key, venv_root, venv_name, package,
               callback=None):
        key = '%s-%s' % (project_key, venv_name)
        self.deployments[key] = Deployment(self, key, project_key, venv_root,
                                           venv_name, package, callback)
        self.deployments[key].start()
        return self.deployments[key]

    def list_deployments(self, by_project_key=None):
        if by_project_key:
            return [deployment for deployment in self.deployments.values()
                    if deployment.project_key == by_project_key]
        return list(self.deployments.values())

    def get_deployment(self, key):
        return self.deployments[key]
