#!python2.7
import os,sys

# Set up basic paths to find pandoc, nodejs, etc.
os.environ['PATH'] = os.pathsep.join(['/usr/local/bin/','/usr/bin','/bin', os.environ.get('PATH','')])
    
from pathomx import Pathomx
Pathomx.main()