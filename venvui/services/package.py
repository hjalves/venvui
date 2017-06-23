# -*- coding: utf-8 -*-

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
    def metadata(path):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError("File not found")

        d = {'type': 'invalid',
             'path': str(path),
             'size': path.stat().st_size,
             'modified': path.stat().st_mtime,
             'pkg_name': str(path.name)}
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
            for k in pkg:
                d[k] = getattr(pkg, k, None)
        return d

    def list_packages(self):
        if not self.package_root.exists() or not self.package_root.is_dir():
            raise NotADirectoryError("Path must be a directory")
        return {path.name: self.metadata(path)
                for path in self.package_root.iterdir()}

    def get_package(self, name):
        return self.metadata(self.package_root / name)

    def save_package(self, from_path, filename):
        Path(from_path).rename(self.package_root / filename)

    async def save_package_from_part(self, part):
        with NamedTemporaryFile(dir=self.temp_path, delete=False) as f:
            await save_part_to_file(f, part)
        self.save_package(f.name, part.filename)
        return self.get_package(part.filename)
