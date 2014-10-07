from matplotlib import cm
import numpy
import re
import os

from requests_toolbelt import MultipartEncoder
import requests

url = 'http://www.kegg.jp/kegg-bin/mcolor_pathway'

node_colors = {}

if input_data is not None:

    mini, maxi = input_data.max().max(), input_data.min().min()
    mapi = np.linspace(mini, maxi, 255)
    color = lambda x: mapi[np.abs(mapi-x).argmin()]

    if mini<0:
        # We're using a linear zero-centered map
        cmap=cm.RdBu(x)

    else:
        # We're using a linear zero-based map
        cmap=cm.PuOr(x)


    scale = utils.calculate_scale([mini, 0, maxi], [9, 1], out=np.around)  # rdbu9 scale

    #for n, m in enumerate(dsi.entities[1]):
    #    xref = self.get_xref( m )

    for n, m in enumerate(dsi.entities[1]):
        if m:

            if 'LIGAND-CPD' in m.databases:
                kegg_id = m.databases['LIGAND-CPD']
                if kegg_id is not None:
                    node_colors[kegg_id] = cmap( color(dsi.data[0, n]) )

            elif 'NCBI-GENE' in m.databases:
                kegg_id = m.databases['NCBI-GENE']
                if kegg_id is not None:
                    node_colors[kegg_id] = cmap( color(dsi.data[0, n]) )

with open(os.path.join(_pathomx_tempdir, 'kegg-pathway-data.txt'), 'w') as tmp:
    tmp.write('#hsa\tData\n')
    for k, c in list(node_colors.items()):
        tmp.write('%s\t%s\n' % (k, c[0]))

    
m = MultipartEncoder(
        fields = {
          'map': config['kegg_pathway_id'],
          'mapping_list': ('filename', open(os.path.join(_pathomx_tempdir, 'kegg-pathway-data.txt'), 'r') ),
          'mode': 'color',
          'submit': 'Exec',
         }
)

r = requests.post(url, data=m, headers={'Content-Type': m.content_type})
html = r.text


from pathomx.displayobjects import Html # We've got the html page; pull out the image
# <img src="/tmp/mark_pathway13818418802193/hsa05200.1.png" name="pathwayimage" usemap="#mapdata" border="0" />
m = re.search('\<img src="(.*)" name="pathwayimage"', html)
img = m.group(1)

m = re.search('^KEGG PATHWAY: (.*)$', html, flags=re.MULTILINE)
title = m.group(1)
output_html = '<html><body><img src="http://www.kegg.jp%s"></body></html>' % img

View = Html(output_html)