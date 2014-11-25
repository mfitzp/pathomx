#!/usr/bin/env python
# coding=utf-8
import os, sys
from copy import copy

import collections
from setuptools import setup, find_packages

__version__ = open('VERSION','rU').read()
sys.path.insert(0,'pathomx')
setup(

    name='Pathomx',
    version=__version__,
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
        'plugins':['*'],
    },
    include_files= [
        ('VERSION','VERSION'),
        ('pathomx/static', 'static'),
        ('pathomx/database', 'database'),
        ('pathomx/plugins', 'plugins'),
        ('pathomx/identities', 'identities'),
        ('pathomx/html', 'html'),
        ('pathomx/icons', 'icons'),
        ('pathomx/demos', 'demos'),
        ],
    
    exclude_package_data = { '': ['README.txt'] },
    entry_points={
        'gui_scripts': [
            'Pathomx = pathomx.Pathomx:main',
        ]
    },

    install_requires = [
            'PyQt5',
            'sip',
            'numpy>=1.5.0',
            'scipy>=0.14.0',
            'pandas>=0.14.0',
            'IPython>=2.0.0',
            'matplotlib>=1.4.0',
            'mplstyler',
            'pyqtconfig',
            'scikit-learn',
            'sklearn',
            'requests',
            'yapsy',

            'mistune',
            'jsonschema',
            'jsonpointer',
            'dateutil',
            'zmq',
            'pygments',
            'pyparsing',
            'markupsafe',
            'wheezy',
            'pydot',
            'jinja2',
            'six',
            'gpml2svg',
            'biocyc',
            'metaviz',
            'mplstyler',
            'icoshift',

            'nmrglue',
            ],


    keywords='bioinformatics data analysis metabolomics research science',
    license='GPL',
    classifiers=['Development Status :: 3 - Alpha',
               'Natural Language :: English',
               'Operating System :: OS Independent',
               'Programming Language :: Python :: 2',
               'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
               'Topic :: Scientific/Engineering :: Bio-Informatics',
               'Topic :: Education',
               'Intended Audience :: Science/Research',
               'Intended Audience :: Education',
              ],

    )