# -*- coding: utf-8 -*-
import numpy as np

from collections import OrderedDict

from . import utils


from matplotlib.figure import Figure
from matplotlib.backend_bases import NavigationToolbar2
from matplotlib.figure import Figure
from matplotlib.colors import Colormap
from matplotlib.path import Path
from matplotlib.patches import BoxStyle, Ellipse
from matplotlib.transforms import Affine2D, Bbox, BboxBase

import matplotlib.cm as cm

def get_figure(width=5, height=4, dpi=100):
    fig = Figure(figsize=(width, height), dpi=dpi) 
    ax = fig.add_subplot( 111 )
    return fig


class EntityBoxStyle(BoxStyle._Base):
    """
    A simple box.
    """

    def __init__(self, pad=0.1):
        """
        The arguments need to be floating numbers and need to have
        default values.

         *pad*
            amount of padding
        """

        self.pad = pad
        super(EntityBoxStyle, self).__init__()

    def transmute(self, x0, y0, width, height, mutation_size):
        """
        Given the location and size of the box, return the path of
        the box around it.

         - *x0*, *y0*, *width*, *height* : location and size of the box
         - *mutation_size* : a reference scale for the mutation.

        Often, the *mutation_size* is the font size of the text.
        You don't need to worry about the rotation as it is
        automatically taken care of.
        """

        # padding
        pad = mutation_size * self.pad

        # width and height with padding added.
        width, height = width + 2.*pad, \
                        height + 2.*pad,

        # boundary of the padded box
        x0, y0 = x0-pad, y0-pad,
        x1, y1 = x0+width, y0 + height

        cp = [(x0, y0),
              (x1, y0), (x1, y1), (x0, y1),
              (x0-pad, (y0+y1)/2.), (x0, y0),
              (x0, y0)]

        com = [Path.MOVETO,
               Path.LINETO, Path.LINETO, Path.LINETO,
               Path.LINETO, Path.LINETO,
               Path.CLOSEPOLY]

        path = Path(cp, com)

        return path
        
# register the custom style
BoxStyle._style_list["entity-tip"] = EntityBoxStyle
        

def spectra(data, figure=None, styles=None):
    if figure is None:
        figure = get_figure()
        
    ax = figure.axes[0]
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.get_xaxis().tick_bottom()
    ax.get_yaxis().tick_left()
    
    ax.cla()

    if data is None:
        assert False

    #if not float in [type(t) for t in dso.scales[1]]:   
    #    # Add fake axis scale for plotting
    #    dso.scales[1] = list(range( len(dso.scales[1])))

    if 'Class' in data.index.names and len( data.index.levels[ data.index.names.index( 'Class' ) ] ) > 1:
        class_idx = data.index.names.index('Class')
        classes = list( data.index.levels[ class_idx ] )
    else:
        class_idx = None
        classes = False
        
    if class_idx is not None and len( classes ) > 1: # We have (more than one) classes
    
        # More than one data row (class) so plot each class
        # Calculate a mean for each class
        data_mean = data.mean(level = class_idx )
        data_max = data_mean.max()
        data_abs_max = data_mean.abs().max()

    else:
        data_mean = data.mean()
        data_max = data.max()
        data_abs_max = data.abs().max()

    data_headers = data_abs_max.index

    # Temporary scale
    if type(data.columns[0]) == float:
        scale = data.columns.values
        is_scale_reversed = scale[0] > scale[-1]
    else:
        scale = np.arange(0, data.shape[1] )
        is_scale_reversed = False
        
    if is_scale_reversed:
        ax.invert_xaxis()
        
    if classes:
    
        # More than one data row (class) so plot each class
        # Calculate a mean for each class
        
        plots = OrderedDict()
        for n,c in enumerate(classes):
            if styles:
                ls = styles.get_style_for_class( c ).line_kwargs
            else:
                ls = {}
                
            row = data_mean.ix[c]
            plots[ c ], = ax.plot(scale, row, **ls)
    
        legend = ax.legend(list(plots.values()),
           list(plots.keys()),
           loc='best') #, bbox_to_anchor=(1, 1))
        legend.get_frame().set_facecolor('k')                      
        legend.get_frame().set_alpha(0.05)     

    else:
        # Only one data row (class) so plot individual data; with a mean line
        data_mean = np.mean(data, axis=0)
        data_individual = data           

        for n in range(0, data_individual.shape[0] ):
            row = data_individual.iloc[n]
        
            ax.plot(scale, row.values, linewidth=0.75, alpha=0.25, color=utils.category10[0])
    
        ax.plot(scale, data_mean.values, linewidth=0.75, color=utils.category10[0])
        
    axlimits = ( ax.get_xlim(), ax.get_ylim() )
    idx = list( np.argsort( data_abs_max ) )[-10:]
    
    '''    
    ylimP = np.amax( dsc.data, axis=0 ) # Positive limit
    ylimN = -np.amax( -dsc.data, axis=0 ) # Negative limit
    ylims = ylimP
    ni = ylimP<-ylimN
    ylims[ ni ] = ylimN[ ni ]
    '''

    anno_label = data_headers[idx]
    anno_scale = scale[idx]
    anno_y = data_max[idx]

    for x,y,l in zip(anno_scale, anno_y, anno_label):
        if y>=0:
            r = '60'
        else:
            r = '-60'
         
        print x, y, l   
        #annotate = ax.text(x, y, l, rotation=r, rotation_mode='anchor', size=6.5, bbox=dict(boxstyle="round,pad=0.1", fc="#eeeeee") )
        #axlimits = self.extend_limits( axlimits, self.get_text_bbox_data_coords(t) )

    #self.ax.set_xlim(axlimits[0].reverse())
    #ax.set_ylim(axlimits[1])
    
    #ax.set_xlabel('ppm')
    #ax.set_ylabel('Rel')

    return figure
    
 
def category_bar(data, figure=None, styles=None):
    if figure == None:
        figure = get_figure()
        
    ax = figure.axes[0]
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.get_xaxis().tick_bottom()
    ax.get_yaxis().tick_left()
    

    if data == None:
        assert False

    # Build x positions; we're grouping by X (entity) then plotting the classes
    ax.cla()
    
    limit_to = 10

    # FIXME: Remove this once UI allows selection of data to plot
    fd = np.mean( dso.data, axis=0 )
    fdm = list(zip( dso.labels[1], fd ))
    sms = sorted(fdm,key=lambda x: abs(x[1]), reverse=True )
    labels = [m for m,s in sms]
    
    plots = OrderedDict()
    classes = dso.classes[0]
    #labels = [e if e != None else dso.labels[1][n] for n,e in enumerate(dso.entities[1][0:limit_to]) ]
    #data = dso.data[:,0:limit_to]
    data = np.array( [ dso.data[ :, dso.labels[1].index( l ) ] for l in labels ] ).T[:,:limit_to]

    #0,1,-,4,5,-,6,7
    
    # 2 classes
    # 3 data points
    
    # 3*2 = 6;  3*(2+1) = 9
    
    # Build spaced sets (around middle value)
    # 0 -0.5->+0.5, 

    xa = []        
    for n,ag in enumerate( data.T ): # Axis groups (can reverse with classes; later)
        xa.append( np.arange(0, len(classes) ) + n*(len(classes)+1) ) # Build table
        
    x = np.array(xa).reshape( len(data.T), len(classes) )
            
    ax.set_xlim( np.min(x)-1, np.max(x)+1 )
              
    for n,c in enumerate(classes):
        cdata = data[n]
        if 'error' in dso.statistics:
            err = dso.statistics['error']['stddev'][:,:limit_to][n]
            yperr = [(0,1)[e>0] for e in cdata ]
            ynerr = [(0,1)[e<0] for e in cdata ]
            
            yperr = np.array(yperr) * err
            ynerr = np.array(ynerr) * err
            yerr = (ynerr, yperr)
        else:
            yerr = None

        ls = styles.get_style_for_class( c )
        plots[c] = self.ax.bar(x[:,n], cdata, align='center', yerr=yerr, **ls.bar_kwargs)

    xticks = np.mean(x,axis=1)
    ax.set_xticks( xticks )
    ax.set_xticklabels(labels, rotation=45, ha='right', rotation_mode='anchor' )


    legend = self.ax.legend(list(plots.values()),
       list(plots.keys()),
       loc='best') #, bbox_to_anchor=(1, 1))
    legend.get_frame().set_facecolor('k')                      
    legend.get_frame().set_alpha(0.05)     
       
    #if options.title:
    #    self.ax.title(options.title)
    #else:
    #    self.ax..title(metabolite)

    #plt.gca().xaxis.set_label_text(options.xlabel)
    #plt.gca().yaxis.set_label_text(options.ylabel)

    # Add some padding either side of graphs
    #plt.xlim( ind[0]-1, ind[-1]+1)

    return figure
