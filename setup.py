#!/usr/bin/env python
# coding=utf-8
import sys
from copy import copy

from setuptools import setup, find_packages

from pathomx.Pathomx import VERSION_STRING

sys.path.insert(0,'pathomx')

# Defaults for py2app / cx_Freeze
default_build_options=dict(
    packages=[
        'PyQt5',
        'numpy',
        'scipy',
        'pandas',
        'IPython',
        'matplotlib',
        'dateutil',
        'zmq',

        'sklearn',
        'sklearn.decomposition',

        'nmrglue',
        'nmrglue.fileio.fileiobase',

        'gpml2svg',
        'icoshift',
        'mplstyler',
        'pyqtconfig',
        ],
    includes=[
        'sip',
        'pydot',
        ],
    excludes=[
        '_xmlplus',
        'test',
        'networkx',
        'wx',
        'mpl-data',
        'Tkinter',
        ],
    )

build_mac = None
build_exe = None
build_py2app = None

executables = []


try:
    from cx_Freeze import setup, Executable
except:
    build_exe = None
    build_mac = None
    excutables = None
else:
    # cx_Freeze setup
    base = None
    exceutables = None

    build_all = dict()
    bdist_msi = dict()

    build_all['include_files']=[
        ('pathomx/static', 'static'),
        ('pathomx/database', 'database'),
        ('pathomx/plugins', 'plugins'),
        ('pathomx/identities', 'identities'),
        ('pathomx/html', 'html'),
        ('pathomx/icons', 'icons'),
        ]

    build_exe = copy(build_all)
    build_mac = copy(build_all)
    
    build_mac['iconfile'] = 'pathomx/static/icon.icns'
    
    base = None
    if sys.platform == "win32":
        base = "Win32GUI"
        build_exe['include_msvcr'] = True
        build_exe['icon'] = 'pathomx/static/icon.ico'
        # FIXME: The following is a hack to correctly copy all files required for 
        # numpy, scipy and nmrglue on Windows. At present cx_Freeze misses a number of 
        # the .pyd files. The fix is to copy *all* of them regardless if they're used.
        # This means bigger binaries (.msi) but they work.
        import os, glob2, numpy, scipy, nmrglue
        explore_dirs = [
            os.path.dirname(numpy.__file__),
            os.path.dirname(scipy.__file__),
            os.path.dirname(nmrglue.__file__),
        ]
        
        files = []
        for d in explore_dirs:
            files.extend( glob2.glob( os.path.join(d, '**', '*.pyd') ) )
            
        # Add DLLs to avoid target needing to install MS distributable packages
        # This is a specific hack to build a distributable version on my own Windows 8 PC
        # PyQt is built using vc110, but only vc90 (Python2.7) is included. This will go away
        # when migrated to Python 3 (also vc110).
        for f in [
            'C:/Windows/System32/msvcr110.dll',
            'C:/Windows/System32/msvcp110.dll',
            #'C:/Windows/WinSxS/amd64_microsoft.vc90.crt_1fc8b3b9a1e18e3b_9.0.30729.8387_none_08e793bfa83a89b5/msvcr90.dll',
            #'C:/Windows/WinSxS/amd64_microsoft.vc90.crt_1fc8b3b9a1e18e3b_9.0.30729.8387_none_08e793bfa83a89b5/msvcp90.dll',
            ]:
        
            build_all['include_files'].append( (f, os.path.basename(f) ) )
            
        # Now we have a list of .pyd files; iterate to build a list of tuples into 
        # include files containing the source path and the basename
        for f in files:
            build_all['include_files'].append( (f, os.path.basename(f) ) )

        shortcut_table = [
            ("DesktopShortcut",        # Shortcut
             "DesktopFolder",          # Directory_
             "Pathomx",           # Name
             "TARGETDIR",              # Component_
             "[TARGETDIR]Pathomx.exe",# Target
             None,                     # Arguments
             None,                     # Description
             None,                     # Hotkey
             None,                     # Icon
             None,                     # IconIndex
             None,                     # ShowCmd
             'TARGETDIR'               # WkDir
             ),
            ("Shortcut",        # Shortcut
             "ProgramMenuFolder",          # Directory_
             "Pathomx",           # Name
             "TARGETDIR",              # Component_
             "[TARGETDIR]Pathomx.exe",# Target
             None,                     # Arguments
             None,                     # Description
             None,                     # Hotkey
             None,                     # Icon
             None,                     # IconIndex
             None,                     # ShowCmd
             'TARGETDIR'               # WkDir
             )             
            ]
        # Change some default MSI options and specify the use of the above defined tables
        bdist_msi['data'] = {"Shortcut": shortcut_table}

        
    # cx_freeze GUI applications require a different base on Windows (the default is for a
    # console application).
    executables=[
        Executable(
            "Pathomx.py",
            base=base,
            copyDependentFiles=True,
            replacePaths=True,
            #shortcutName="Pathomx",
            #shortcutDir="ProgramMenuFolder",
            )]

    # Apply default build options to cx/py2app build targets
    build_exe.update( default_build_options )
    build_mac.update( default_build_options )
    

setup(

    name='Pathomx',
    version=VERSION_STRING,
    author='Martin Fitzpatrick',
    author_email='martin.fitzpatrick@gmail.com',
    url='https://github.com/pathomx/pathomx',
    download_url='https://github.com/pathomx/pathomx/zipball/master',
    description='Metabolic pathway visualisation and analysis.',
    long_description='Pathomx is workflow-based scientific data processing, analysis and \
        visualisation too. Built on IPython notebooks it allows rapid prototyping of \
        analysis approaches, sharing of workflows and export of generated IPython notebooks \
        that capture the approach. The included notebook tools are aimed towards the analysis of \
        metabolomic data inlucindg: NMR data processing, integration with the BioCyc database, \
        dynamic metabolic pathway drawing and support for GPML/KEGG.',
        
    packages = find_packages(),
    include_package_data = True,
    package_data = {
        '': ['*.txt', '*.rst', '*.md'],
    },
    exclude_package_data = { '': ['README.txt'] },

    executables = executables,

    entry_points={
        'gui_scripts': [
            'Pathomx = pathomx.Pathomx:main',
        ]
    },

    install_requires = [
            #'PyQt5',
            'numpy>=1.5.0',
            'wheezy.template>=0.1.135',
            'gpml2svg>=0.1.0',
            'numpy>=1.8.0',
            'scipy>=0.14.0',
            'pandas>=0.14.0',
            'IPython>=2.0.0',
            'matplotlib>=1.4.0',
            'dateutil',
            'zmq',

            'sklearn',
            'sklearn.decomposition',

            'nmrglue',
            'nmrglue.fileio.fileiobase',

            'gpml2svg',
            'icoshift',
            'mplstyler',
            'pyqtconfig',

            ],

    keywords='bioinformatics data analysis metabolomics research science',
    license='GPL',
    classifiers=['Development Status :: 5 - Production/Stable',
               'Natural Language :: English',
               'Operating System :: OS Independent',
               'Programming Language :: Python :: 2',
               'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
               'Topic :: Scientific/Engineering :: Bio-Informatics',
               'Topic :: Education',
               'Intended Audience :: Science/Research',
               'Intended Audience :: Education',
              ],

    # cx_freeze/py2app settings for building the .app file
    options={
        "build_exe": build_exe,
        "build_mac": build_mac,
        "bdist_msi": bdist_msi,
        #"py2app": build_py2app
    },
    app=[ 'Pathomx.py' ],
    #setup_requires=["py2app"],

    )
