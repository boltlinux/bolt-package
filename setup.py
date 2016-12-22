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
    author_email='tobias.koch@nonterra.com',
    license='MIT',
    package_dir={'': 'lib'},
    platforms=['Linux'],
    packages=['com.nonterra.bolt.package', 'com.nonterra.bolt.debian'],

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