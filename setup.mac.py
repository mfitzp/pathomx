#!/usr/bin/env python
# coding=utf-8
import os, sys
from copy import copy

import collections
from setuptools import setup, find_packages

__version__ = open('VERSION','rU').read()
sys.path.insert(0,'pathomx')

# Defaults for py2app / cx_Freeze
build_py2app=dict(
    argv_emulation=True,
    includes=[
        'PyQt4',
        "PyQt4.uic.port_v3.proxy_base",

        'numpy',
        'scipy',
        'pandas',
        'matplotlib',
        'dateutil',
        'requests',

        'IPython',
        'IPython.qt.client',
        'IPython.qt.inprocess',
        'IPython.qt.manager',
        'IPython.utils',

        'sklearn',
        'sklearn.decomposition',

        'nmrglue',
        'nmrglue.fileio.fileiobase',

        'gpml2svg',
        'icoshift',
        'mplstyler',
        'pyqtconfig',
        'custom_exceptions',
        
        "zmq",
        "zmq.utils.garbage",
        "zmq.backend.cython",
        
        "pygments",
        'pygments.styles',
        'pygments.styles.default',

        'sip',
        'pydot',
        
        'jinja2',
        'jinja2.ext',
        
        ],
    excludes=[
        '_xmlplus',
        'test',
        'networkx',
        'wx',
        'mpl-data',
        'Tkinter',
        "collections.abc",
        "PyQt5",
        ],  
    resources=[
        'pathomx/database',
        'pathomx/html',
        'pathomx/icons',
        'pathomx/identities',
        'pathomx/plugins',
        'pathomx/static',
        'pathomx/translations',
        'VERSION',
        'README.md',
    ],
    plist=dict(
        CFBundleName = "Pathomx",
        CFBundleShortVersionString = __version__,
        CFBundleGetInfoString = "Pathomx %s" % __version__,
        CFBundleExecutable = "Pathomx",
        CFBundleIdentifier = "org.pathomx.pathomx",
    ),    
    iconfile='pathomx/static/icon.icns',
    )

setup(

    name='Pathomx',
    version=__version__,
    author='Martin Fitzpatrick',
    packages = find_packages(),
    include_package_data = True,
    app=['Pathomx.py'],
    options={
        'py2app': build_py2app,
        },
    setup_requires=['py2app'],
    )
