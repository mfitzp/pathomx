#!/usr/bin/env python

from SOAPpy import WSDL

wsdl = 'http://soap.genome.jp/KEGG.wsdl'
serv = WSDL.Proxy(wsdl)

results = serv.get_compounds_by_pathway('path:eco00020')
print results
