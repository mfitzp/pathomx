#!/usr/bin/env python
# coding=utf-8

import unittest

from my_program.helpers import fn


class Test(unittest.TestCase):
    """Unit tests for utils.fn()"""

    def test_fn(self):
        """Test result"""
        value = True
        result = fn(value)
        self.assertEqual(value, result)
        
    #def test_doctest(self):
        #import doctest
        #import my_program.utils
        #doctest.testmod(my_program.utils)


if __name__ == "__main__":
    unittest.main()
