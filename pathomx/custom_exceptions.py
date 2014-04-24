from __future__ import unicode_literals
import logging
logging.debug('Loading custom_exceptions.py')

import sys

if sys.version_info < (3, 0):  # Python 2 only
    from exceptions import Exception


class PathomxIncorrectFileFormatException(Exception):
    pass

    
class PathomxIncorrectFileStructureException(Exception):
    pass


class PathomxExternalResourceTimeoutException(Exception):
    pass


class PathomxExternalResourceUnavailableException(Exception):
    pass
