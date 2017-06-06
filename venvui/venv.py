# -*- coding: utf-8 -*-

from pathlib import Path


class VirtualEnvService:

    def __init__(self, venv_path):
        self.venv_path = Path(venv_path)
        assert self.venv_path.exists()
        assert self.venv_path.is_dir()

    @staticmethod
    def _get_info(path):
        return {'modified': path.stat().st_mtime,
                'path': str(path)}

    def create(self, name):
        pass

    def list_virtualenvs(self):
        return {path.name: self._get_info(path)
                for path in self.venv_path.iterdir()}
