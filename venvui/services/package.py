# -*- coding: utf-8 -*-

from pathlib import Path

import pkginfo


class PackageService:
    def __init__(self, package_root):
        self.package_root = Path(package_root)
        if not self.package_root.exists() or not self.package_root.is_dir():
            raise NotADirectoryError("Path must be a directory")

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
