#!/usr/bin/env python
# coding=utf-8
import sys
from copy import copy

from setuptools import setup, find_packages

version_string = '1.5.0'

sys.path.insert(0,'metapath')

# Defaults for py2app / cx_Freeze
default_build_options=dict(
    packages=[
        'PyQt5',
        'numpy',
        'scipy',
        'nmrglue',
        'gpml2svg',
        'poster.encode',
        'wheezy.template',
        'sklearn',
        'sklearn.decomposition',
        'icoshift',
        'nmrglue.fileio.fileiobase',
        'matplotlib',
        ],
    includes=[
        'sip',
        'pydot',
        ],
    excludes=[
        '_xmlplus',
        'IPython',
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
        ('metapath/static', 'static'),
        ('metapath/database', 'database'),
        ('metapath/plugins', 'plugins'),
        ('metapath/identities', 'identities'),
        ('metapath/html', 'html'),
        ('metapath/icons', 'icons'),
        ]

    build_exe = copy(build_all)
    build_mac = copy(build_all)
    
    build_mac['iconfile'] = 'metapath/static/icon.icns'
    
    base = None
    if sys.platform == "win32":
        base = "Win32GUI"
        build_exe['include_msvcr'] = True
        build_exe['icon'] = 'metapath/static/icon.ico'
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
            
        # Now we have a list of .pyd files; iterate to build a list of tuples into 
        # include files containing the source path and the basename
        for f in files:
            build_all['include_files'].append( (f, os.path.basename(f) ) )

        shortcut_table = [
            ("DesktopShortcut",        # Shortcut
             "DesktopFolder",          # Directory_
             "MetaPath",           # Name
             "TARGETDIR",              # Component_
             "[TARGETDIR]MetaPath.exe",# Target
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
             "MetaPath",           # Name
             "TARGETDIR",              # Component_
             "[TARGETDIR]MetaPath.exe",# Target
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
            "metapath/MetaPath.py",
            base=base,
            copyDependentFiles=True,
            replacePaths=True,
            #shortcutName="MetaPath",
            #shortcutDir="ProgramMenuFolder",
            )]

    # Apply default build options to cx/py2app build targets
    build_exe.update( default_build_options )
    build_mac.update( default_build_options )
    

setup(

    name='MetaPath',
    version=version_string,
    author='Martin Fitzpatrick',
    author_email='martin.fitzpatrick@gmail.com',
    url='https://github.com/mfitzp/metapath',
    download_url='https://github.com/mfitzp/metapath/zipball/master',
    description='Metabolic pathway visualisation and analysis.',
    long_description='MetaPath is a tool for the analysis of metabolic pathway and \
        associated visualisation of experimental data. Built on the MetaCyc database it \
        provides an interactive map in which multiple pathways can be simultaneously \
        visualised. Multiple annotations from the MetaCyc database are available including \
        synonyms, associated reactions and pathways and database unification links.',

    packages = find_packages(),
    include_package_data = True,
    package_data = {
        '': ['*.txt', '*.rst', '*.md'],
    },
    exclude_package_data = { '': ['README.txt'] },

    executables = executables,

    entry_points = {
        'gui_scripts': [
            'MetaPath = metapath.MetaPath:main',
        ]
    },

    install_requires = [
#            'PySide>=1.1.1',
            'numpy>=1.5.0',
            'wheezy.template>=0.1.135',
            'gpml2svg>=0.1.0',
#            'sip',
#            'matplotlib>=1.2.1'
            ],

    keywords='bioinformatics metabolomics research analysis science',
    license='GPL',
    classifiers=['Development Status :: 4 - Beta',
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
    app=[ 'metapath/MetaPath.py' ],
    #setup_requires=["py2app"],

    )