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
        'PyQt5',
        "PyQt5.uic.port_v3.proxy_base",

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
        'sklearn.cross_decomposition',
        
        'nose',
        'nose.tools',
        
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
        
        'rpy2',
        'pymatbridge',
        
        ],
    excludes=[
        '_xmlplus',
        'test',
        'networkx',
        'wx',
        'mpl-data',
        'Tkinter',
        "collections.abc",
        'nose',
        'PyQt4',
        'PySide',
        'debug',
        # Bizarre inclusions with build ?due to sip error
        'youtube_dl',
        'astroid',
        'werkzeug',
        'smartypants',
        'pep8ify',
        'modernize',
        'pyflakes',
        'frosted',
        'flask',
        'jedi',
        'autopep8',
        'twiggy',
        'pyqtgraph',
        'growl',
        'feedgenerator',
        'sphinx',
        
        ],  
    resources=[
        'pathomx/database',
        'pathomx/demos',
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
    #/usr/local/Cellar/qt5/5.3.2/plugins
    qt_plugins=[
        'platforms/libqcocoa.dylib',
        'imageformats',
        'printsupport/libcocoaprintersupport.dylib',
        'accessible',
        ],
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
