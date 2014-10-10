# The MIT License (MIT) Copyright (c) 2014 Christopher DeBoever
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software 
# and associated documentation files (the "Software"), to deal in the Software without restriction, 
# including without limitation the rights to use, copy, modify, merge, publish, distribute, 
# sublicense, and/or sell copies of the Software, and to permit persons to whom the Software 
# is furnished to do so, subject to the following conditions: The above copyright notice 
# and this permission notice shall be included in all copies or substantial portions of the 
# Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR 
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE 
# FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR 
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
# DEALINGS IN THE SOFTWARE. 

# Modifications for Pathomx by Martin Fitzpatrick (c) 2014 

import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import colorConverter
import scipy.spatial.distance as distance
import scipy.cluster.hierarchy as sch
import matplotlib.cm as cm

import pandas as pd
import numpy as np

# helper for cleaning up axes by removing ticks, tick labels, frame, etc.
def clean_axis(ax):
    """Remove ticks, tick labels, and frame from axis"""
    ax.get_xaxis().set_ticks([])
    ax.get_yaxis().set_ticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)


# make norm
vmin = input_data.min().min()
vmax = input_data.max().max()
print("Range in data %f...%f" % (vmin, vmax))
vmax = max([vmax,abs(vmin)]) # choose larger of vmin and vmax
vmin = vmax * -1
print("Normalised to %f...%f" % (vmin, vmax))
my_norm = mpl.colors.Normalize(vmin, vmax)

# dendrogram single color
sch.set_link_color_palette(['black'])

# cluster
row_pairwise_dists = distance.squareform(distance.pdist(input_data))
row_clusters = sch.linkage(row_pairwise_dists,method=config['method'])

col_pairwise_dists = distance.squareform(distance.pdist(input_data.T))
col_clusters = sch.linkage(col_pairwise_dists,method=config['method'])

# heatmap with row names
View = plt.figure(figsize=(12,8))
heatmapGS = gridspec.GridSpec(2,2,wspace=0.0,hspace=0.0,width_ratios=[0.25,1],height_ratios=[0.25,1])

### col dendrogram ###
col_denAX = View.add_subplot(heatmapGS[0,1])
col_denD = sch.dendrogram(col_clusters,color_threshold=np.inf)
clean_axis(col_denAX)

rowGSSS = gridspec.GridSpecFromSubplotSpec(1,2,subplot_spec=heatmapGS[1,0],wspace=0.0,hspace=0.0,width_ratios=[1,0.05])

### row dendrogram ###
row_denAX = View.add_subplot(rowGSSS[0,0])
row_denD = sch.dendrogram(row_clusters,color_threshold=np.inf,orientation='right')
clean_axis(row_denAX)

### row colorbar ###
if 'Class' in input_data.index.names:
    class_idx = input_data.index.names.index('Class')
    
    classcol = [ styles.get_style_for_class(x[class_idx]).color for x in input_data.index.values[row_denD['leaves']]]
    classrgb = np.array([colorConverter.to_rgb(c) for c in classcol]).reshape(-1,1,3)
    row_cbAX = View.add_subplot(rowGSSS[0,1])
    row_axi = row_cbAX.imshow(classrgb,interpolation='nearest',aspect='auto',origin='lower')
    clean_axis(row_cbAX)
    

### heatmap ####
heatmapAX = View.add_subplot(heatmapGS[1,1])

axi = heatmapAX.imshow(input_data.iloc[row_denD['leaves'],col_denD['leaves']], interpolation='nearest',aspect='auto',origin='lower'
                       ,norm=my_norm,cmap=cm.RdBu_r)
clean_axis(heatmapAX)

#class_idx = input_data.index.names.index('Class')
#classes = [v[class_idx] for v in input_data.index.values]

## row labels ##
if input_data.shape[0] <= 100:
    heatmapAX.set_yticks(range(input_data.shape[0]))
    heatmapAX.yaxis.set_ticks_position('right')
    ylabels = [ " ".join([str(t) for t in i]) if type(i) == tuple else str(i) for i in input_data.index[row_denD['leaves']]]
    heatmapAX.set_yticklabels(ylabels)

## col labels ##
if input_data.shape[1] <= 100:
    heatmapAX.set_xticks(range(input_data.shape[1]))
    xlabels = [ " ".join([str(t) for t in i]) if type(i) == tuple else str(i) for i in input_data.columns[col_denD['leaves']]]
    xlabelsL = heatmapAX.set_xticklabels(xlabels)
    # rotate labels 90 degrees
    for label in xlabelsL:
        label.set_rotation(90)

# remove the tick linesss
for l in heatmapAX.get_xticklines() + heatmapAX.get_yticklines(): 
    l.set_markersize(0)
    
heatmapGS.tight_layout(View,h_pad=0.1,w_pad=0.5)
