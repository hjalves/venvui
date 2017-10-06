# -*- coding: utf-8 -*-

from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

import pkginfo

from venvui.utils.misc import save_part_to_file


class PackageService:
    def __init__(self, package_root, temp_path):
        self.package_root = Path(package_root)
        self.temp_path = Path(temp_path)
        if not self.package_root.exists() or not self.package_root.is_dir():
            raise NotADirectoryError("%s must be a directory" %
                                     self.package_root)
        if not self.temp_path.exists() or not self.temp_path.is_dir():
            raise NotADirectoryError("%s must be a directory" % self.temp_path)

    @staticmethod
    def package_info(path):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError("File not found")

        d = {'type': 'unknown',
             'path': str(path),
             'size': path.stat().st_size,
             'modified': datetime.utcfromtimestamp(path.stat().st_mtime),
             'filename': str(path.name)}
        pkg = None

        try:
            if path.suffix == '.whl':
                pkg = pkginfo.Wheel(path)
                d['type'] = 'wheel'
            elif path.suffix in ('.gz', '.bz2'):
                pkg = pkginfo.SDist(path)
                d['type'] = 'sdist'
        except ValueError as e:
            d['error'] = str(e)

        if pkg:
            d['metadata'] = {k: getattr(pkg, k, None) for k in pkg}
        return d

    def list_packages(self):
        if not self.package_root.exists() or not self.package_root.is_dir():
            raise NotADirectoryError("Path must be a directory")
        for path in self.package_root.iterdir():
            yield self.package_info(path)

    def get_package(self, name):
        try:
            return self.package_info(self.package_root / name)
        except FileNotFoundError:
            return None

    def save_package(self, from_path, filename):
        Path(from_path).rename(self.package_root / filename)

    async def save_package_from_part(self, part):
        with NamedTemporaryFile(dir=self.temp_path, delete=False) as f:
            await save_part_to_file(f, part)
        self.save_package(f.name, part.filename)
        return self.get_package(part.filename)
