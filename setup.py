#!/usr/bin/env python3

"""Bolt OS packaging scripts and tools."""

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

setup(
    name='bolt-package',
    version='1.0.0',
    url='https://github.com/tobijk/bolt-package',
    author='Tobias Koch',
    author_email='tobias.koch@gmail.com',
    license='MIT',
    packages=['org.boltlinux', 'org.boltlinux.package', 'org.boltlinux.deb2bolt'],
    package_dir={'': 'lib'},
    data_files=[
        ('bin', [
            'bin/bolt-pack',
            'bin/deb2bolt',
            'bin/bolt-repo-index',
            'bin/bolt-pkg-dbd'
        ]),
        ('share/bolt-pack/relaxng', ['relaxng/package.rng.xml']),
        ('share/bolt-pack/helpers', [
            'helpers/arch.sh',
            'helpers/python.sh'
        ])
    ],
    platforms=['Linux'],

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3'
    ],

    keywords='boltOS packaging development',
    description='Bolt OS packaging scripts and tools',
    long_description='Bolt OS packaging scripts and tools',
)
