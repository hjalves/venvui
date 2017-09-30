#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='venvui',
    version='0.1a2',
    description='An user interface to manage Python projects and virtual '
                'environments.',
    url='https://github.com/hjalves/venvui',
    author='Humberto Alves',
    author_email='hjalves@live.com',
    license='MIT',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='venvui',
    packages=find_packages(),
    install_requires=[
        'aiohttp',
        'aiohttp-cors',
        'colorlog',
        'toml',
        'pkginfo'
    ],
    entry_points={
        'console_scripts': [
            'venvui = venvui.app:main',
        ]
    },
    #include_package_data=True,
    zip_safe=False,
)
