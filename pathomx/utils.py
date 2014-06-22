from __future__ import unicode_literals
import logging

import re
import os
import sys
import errno
import csv
import codecs
import io
from collections import defaultdict

import cStringIO

import numpy as np

from .qt import *

try:
    import xml.etree.cElementTree as et
except ImportError:
    import xml.etree.ElementTree as et

try:
    import cPickle as pickle
except:
    import pickle

rdbu9 = [0, '#b2182b', '#d6604d', '#f4a582', '#fddbc7', '#cccccc', '#d1e5f0', '#92c5de', '#4393c3', '#2166ac']
rdbu9c = [0, '#ffffff', '#000000', '#000000', '#000000', '#000000', '#000000', '#000000', '#ffffff', '#ffffff']
category10 = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

from matplotlib.figure import Figure
from matplotlib.axes import Subplot


def _convert_list_type_from_XML(vs):
    '''
    Lists are a complex type with possibility for mixed sub-types. Therefore each
    sub-entity must be wrapped with a type specifier.
    '''
    vlist = vs.findall('ListItem') + vs.findall('ConfigListItem')  # ConfigListItem is legacy
    l = []
    for xconfig in vlist:
        v = xconfig.text
        if xconfig.get('type') in CONVERT_TYPE_FROM_XML:
            # Recursive; woo!
            v = CONVERT_TYPE_FROM_XML[xconfig.get('type')](xconfig)
        l.append(v)
    return l


def _convert_list_type_to_XML(co, vs):
    '''
    Lists are a complex type with possibility for mixed sub-types. Therefore each
    sub-entity must be wrapped with a type specifier.
    '''
    for cv in vs:
        c = et.SubElement(co, "ListItem")
        t = type(cv).__name__
        c.set("type", t)
        c = CONVERT_TYPE_TO_XML[t](c, cv)
    return co


def _convert_dict_type_from_XML(vs):
    '''
    Dicts are a complex type with possibility for mixed sub-types. Therefore each
    sub-entity must be wrapped with a type specifier.
    '''
    vlist = vs.findall('DictItem')
    d = {}
    for xconfig in vlist:
        v = xconfig.text
        if xconfig.get('type') in CONVERT_TYPE_FROM_XML:
            # Recursive; woo!
            v = CONVERT_TYPE_FROM_XML[xconfig.get('type')](xconfig)
        d[xconfig.get('key')] = v
    return d


def _convert_dict_type_to_XML(co, vs):
    '''
    Dicts are a complex type with possibility for mixed sub-types. Therefore each
    sub-entity must be wrapped with a type specifier.
    '''
    for k, v in vs.items():
        c = et.SubElement(co, "DictItem")
        t = type(v).__name__
        c.set("type", t)
        c.set("key", k)
        c = CONVERT_TYPE_TO_XML[t](c, v)
    return co


def _apply_text_str(co, s):
    co.text = str(s)
    return co

CONVERT_TYPE_TO_XML = {
    'str': _apply_text_str,
    'unicode': _apply_text_str,
    'int': _apply_text_str,
    'float': _apply_text_str,
    'bool': _apply_text_str,
    'list': _convert_list_type_to_XML,
    'tuple': _convert_list_type_to_XML,
    'dict': _convert_dict_type_to_XML,
}

CONVERT_TYPE_FROM_XML = {
    'str': lambda x: str(x.text),
    'unicode': lambda x: str(x.text),
    'int': lambda x: int(x.text),
    'float': lambda x: float(x.text),
    'bool': lambda x: bool(x.text.lower() == 'true'),
    'list': _convert_list_type_from_XML,
    'tuple': _convert_list_type_from_XML,
    'dict': _convert_dict_type_from_XML,
}


def sigstars(p):
    # Return appropriate number of stars or ns for significance

    if (p <= 0.0001):
        s = '****'
    elif (p <= 0.001):
        s = '***'
    elif (p <= 0.01):
        s = '**'
    elif (p <= 0.05):
        s = '*'
    else:
        s = 'ns'
    return s


def calculate_scale(range, output, out=float):
# Calculate a scale using equally input points (min,max) or (min, 0, max)
# mapped to the output range; returns a lambda function to perform the conversion

    if len(range) == 3:  # Have midpoint
        intersect_in = range[1]
    else:
        intersect_in = range[0]

    maxi = max([abs(x) for x in range])
    mini = -maxi

    # Calculate slope in = x, out = y
    # slope = y2-y1/x2-x1
    m = (output[1] - output[0]) / (maxi - mini)
    x1 = range[0]
    y1 = output[0]
    mino = min(output)
    maxo = max(output)

    scale = lambda x: np.clip(out((m * x) - (m * x1) + y1), mino, maxo)
    print("Scale generator...")
    return scale


def calculate_rdbu9_color(scale, value):
    # Rescale minima-maxima to range of rdbu9 (9)
    try:
        rdbu9col = int(scale(value))
    except:
        return None  # Fill zero nothing if not known
    return (rdbu9[rdbu9col], rdbu9c[rdbu9col], rdbu9col)


def invert_direction(direction):
    if direction == 'forward':
        return 'back'
    elif direction == 'back':
        return 'forward'
    else:
        return direction


def swap(ino, outo):
    return (outo, ino)


def nonull(stream):
    for line in stream:
        yield line.replace('\x00', '')



if sys.version_info < (3, 0):  # Python 2 only


    class UnicodeReader:
        """
        A CSV reader which will iterate over lines in the CSV file "f",
        which is encoded in the given encoding.
        """

        def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwargs):

            self.reader = csv.reader(f, **kwargs)
            self.encoding = encoding
            #f = UTF8Recoder(f, encoding)
            #self.reader = csv.reader(f, dialect=dialect, **kwds)

        def __next__(self):
            row = self.reader.__next__()
            return [str(c, self.encoding) for c in row]

        def __iter__(self):
            return self

        def next(self):
            row = self.reader.next()
            return [unicode(c, self.encoding) for c in row]


    class UnicodeWriter:
        """
        A CSV writer which will write rows to CSV file "f",
        which is encoded in the given encoding.
        """

        def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwargs):
            # Redirect output to a queue
            self.queue = cStringIO.StringIO()
            self.writer = csv.writer(self.queue, dialect=dialect, **kwargs)
            self.stream = f
            self.encoder = codecs.getincrementalencoder(encoding)()

        def writerow(self, row):
            row = [unicode(s) for s in row]
            self.writer.writerow([s.encode("utf-8") for s in row])
            # Fetch UTF-8 output from the queue ...
            data = self.queue.getvalue()
            data = data.decode("utf-8")
            # ... and reencode it into the target encoding
            data = self.encoder.encode(data)
            # write to the target stream
            self.stream.write(data)
            # empty queue
            self.queue.truncate(0)

        def writerows(self, rows):
            for row in rows:
                self.writerow(row)

else:
    from csv import reader as UnicodeReader
    from csv import writer as UnicodeWriter


class MutexDict(dict):

    def __init__(self, *args, **kwargs):
        self.mutex = QMutex()
        return super(MutexDict, self).__init__(*args, **kwargs)

    def __getattribute__(self, attr):
        if attr == 'mutex':
            return super(MutexDict, self).__getattribute__(attr)
        else:
            # Lock all other attributes with the mutex
            with QMutexLocker(self.mutex):
                return super(MutexDict, self).__getattribute__(attr)


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


# http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
def which(program):
    import os

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    def ext_candidates(fpath):
        yield fpath
        for ext in os.environ.get("PATHEXT", "").split(os.pathsep):
            yield fpath + ext

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            for candidate in ext_candidates(exe_file):
                if is_exe(candidate):
                    return candidate

    return None


def find_packager():

    import sys
    frozen = getattr(sys, 'frozen', None)

    if not frozen:
        # COULD be certain cx_Freeze options or bundlebuilder, nothing to worry about though
        return None
    elif frozen in ('dll', 'console_exe', 'windows_exe'):
        return 'py2exe'
    elif frozen in ('macosx_app', ):
        return 'py2app'
    elif frozen is True:
        return True  # it doesn't ALWAYS set this return 'cx_Freeze' 
    else:
        return '<unknown packager: %r>' % (frozen, )

# Get current running script folder (Pathomx app folder)
pkg = find_packager()
if pkg == None:
    scriptdir = os.path.dirname(os.path.realpath(__file__))  # .rpartition('/')[0]
elif pkg == True:
    scriptdir = os.path.dirname(sys.executable)
elif pkg == 'py2app':
    #'/Applications/Pathomx.app/Contents/Resources'
    scriptdir = os.environ['RESOURCEPATH']
elif pkg == 'py2exe':
    scriptdir = os.path.dirname(str(sys.executable, sys.getfilesystemencoding()))
