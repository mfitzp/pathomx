import re, os, sys, errno
import csv, codecs, cStringIO
from collections import defaultdict

import numpy as np

rdbu9 =  [0, '#b2182b', '#d6604d', '#f4a582', '#fddbc7', '#cccccc', '#d1e5f0', '#92c5de', '#4393c3', '#2166ac']
rdbu9c = [0, '#ffffff', '#000000', '#000000', '#000000', '#000000', '#000000', '#000000', '#ffffff', '#ffffff']
category10 = ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#8c564b','#e377c2','#7f7f7f','#bcbd22','#17becf']

def sigstars(p):
    # Return appropriate number of stars or ns for significance

    if (p<=0.0001):
        s = '****'
    elif (p<=0.001):
        s = '***'
    elif (p<=0.01):
        s = '**'
    elif (p<=0.05):
        s = '*'
    else:
        s = 'ns'
    return s


def calculate_scale(range, output, out=float):
# Calculate a scale using equally input points (min,max) or (min, 0, max)
# mapped to the output range; returns a lambda function to perform the conversion
    
    if len(range)==3: # Have midpoint
        intersect_in = range[1]
    else:
        intersect_in = range[0]

    maxi = max( [ abs(x) for x in range ] )
    mini = -maxi
        
    # Calculate slope in = x, out = y
    # slope = y2-y1/x2-x1
    m = (output[1]-output[0]) / (maxi-mini)
    x1 = range[0]
    y1 = output[0]
    mino = min(output)
    maxo = max(output)

    scale = lambda x: np.clip( out( (m*x)-(m*x1)+y1 ), mino, maxo )
    print "Scale generator..."
    return scale
    
def calculate_rdbu9_color(scale, value):
    # Rescale minima-maxima to range of rdbu9 (9)
    try:
        rdbu9col = int( scale(value) )
    except:
        return None # Fill zero nothing if not known
    return ( rdbu9[ rdbu9col ], rdbu9c[ rdbu9col ], rdbu9col)



def read_metabolite_datafile( filename, options ):
    
    # Read in data for the graphing metabolite, with associated value (generate mean)
    reader = csv.reader( open( filename, 'rU'), delimiter=',', dialect='excel')
    # Find matching metabolite column
    hrow = reader.next()
    try:
        metabolite_column = hrow.index( options.metabolite )
        print "'%s' found" % (options.metabolite)
        metabolites = [ options.metabolite ]
    except:
        all_metabolites = hrow[2:]
        metabolites = filter(lambda x:re.match('(.*)' + options.metabolite + '(.*)', x), all_metabolites)
        if len(metabolites) ==0:
            print "Metabolite not found, try again. Pick from one of:"
            print ', '.join( sorted(all_metabolites) )  
            exit()
        elif len(metabolites) > 1:
            print "Searched '%s' and found multiple matches:" % (options.metabolite)
            print ', '.join( sorted(metabolites) )
            if not options.batch_mode:
                print "To process all the above together use batch mode -b"
                exit()
        elif len(metabolites) ==1:
            print "Searched '%s' and found match in '%s'" % (options.metabolite, metabolites[0])
    
    
    # Build quants table for metabolite classes
    allquants = dict()
    for metabolite in metabolites:
        allquants[ metabolite ] = defaultdict(list)
    
    ymin = 0
    ymax = 0
    
    for row in reader:
        if row[1] != '.': # Skip excluded classes # row[1] = Class
            for metabolite in metabolites:
                metabolite_column = hrow.index( metabolite )   
                if row[ metabolite_column ]:
                    allquants[metabolite][ row[1] ].append( float(row[ metabolite_column ]) )
                    ymin = min( ymin, float(row[ metabolite_column ]) )
                    ymax = max( ymax, float(row[ metabolite_column ]) )
                else:
                    allquants[metabolite][ row[1] ].append( 0 )
        
    return ( metabolites, allquants, (ymin,ymax) )
    
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

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
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
      

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise
            
def find_packager():

    import sys
    frozen = getattr(sys, 'frozen', None)

    if not frozen:
        # COULD be certain cx_Freeze options or bundlebuilder, nothing to worry about though
        return None 
    elif frozen in ('dll', 'console_exe', 'windows_exe'):
        return 'py2exe' 
    elif frozen in ('macosx_app',):
        return 'py2app' 
    elif frozen is True:
        return True # it doesn't ALWAYS set this return 'cx_Freeze' 
    else:
        return '<unknown packager: %r>' % (frozen,) 
        

# Get current running script folder (Pathomx app folder)
pkg = find_packager()
if pkg == None:
    scriptdir = os.path.dirname( os.path.realpath(__file__) ) #.rpartition('/')[0]
elif pkg == True:
    scriptdir = os.path.dirname(sys.executable)
elif pkg == 'py2app':
    #'/Applications/Pathomx.app/Contents/Resources'
    scriptdir = os.environ['RESOURCEPATH']
elif pkg == 'py2exe':
    scriptdir = os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding( )))



