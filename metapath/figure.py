import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pylab as pl


def heatmap( data, labelsX=[], labelsY=[], dpi=100, remove_empty_rows=True, remove_empty_cols=False ): #, fname=None, dpi=300, format='png'):
    plt.rc('font', **{'family' : 'Calibri',
            'weight' : 'bold',
            'size'   : 9.5})

    # Red/Green heatmap colormap
    cdict = {'red': ((0.0, 0.0, 0.0),
                     (0.5, 0.0, 0.0),
                     (1.0, 1.0, 1.0)),
             'green': ((0.0, 1.0, 1.0),
                       (0.5, 0.0, 0.0),
                       (1.0, 0.0, 0.0)),
             'blue': ((0.0, 0.0, 0.0),
                    (0.5, 0.0, 0.0),
                     (1.0, 0.0, 0.0))}
                     
    # Red/Blue heatmap colormap
    cdict = {'red': ((0.0, 178.0/255, 178.0/255),
                     (0.5, 247.0/255, 247.0/255),
                     (1.0,  33.0/255,  33.0/255)),
             'green':((0.0, 24.0/255,  24.0/255),
                     (0.5, 247.0/255, 247.0/255),
                     (1.0, 102.0/255, 102.0/255)),
             'blue': ((0.0, 43.0/255,  43.0/255),
                     (0.5, 247.0/255, 247.0/255),
                     (1.0, 172.0/255, 172.0/255))}
    
    #my_cmap = matplotlib.colors.LinearSegmentedColormap('my_colormap',cdict,256)
    
    if remove_empty_rows:
        mask = ~np.isnan(data).all(axis=1)
        data = data[mask]
        labelsY = [l for l,m in zip(labelsY,mask) if m]

    if remove_empty_cols:
        mask = ~np.isnan(data).all(axis=0)
        data = data.T[mask.T]
        labelsX = [l for l,m in zip(labelsX,mask) if m]

    xdim = data.shape[1]
    ydim = data.shape[0]

    # Preferable would be to sort by the total for each row
    # can then use that to sort the labels list also
    totals = np.ma.masked_invalid(data).sum(1).data # Get sum for rows, ignoring NaNs
    si = totals.argsort()[::-1]
    data = data[si] # Sort
    labelsY = list( np.array( labelsY )[si] ) # Sort Ylabels via numpy array.

    
    fig = plt.figure(figsize=(float(xdim)*0.275,float(ydim)*0.275), tight_layout=True, dpi=dpi)
    fig.set_facecolor('white')

    masked_data = np.ma.array(data, mask=np.isnan(data))

    vmax = max( abs( np.amin( masked_data ) ), abs( np.amax( masked_data ) ) )
    if vmax == 0:
        vmax = 1
    
    ax = plt.subplot(111)
        
    ax.pcolormesh(masked_data, alpha=0.8, vmin=-vmax,vmax=+vmax, cmap=plt.cm.RdBu_r) #my_cmap) #plt.cm.RdBu)

    ax.grid(False)
    ax.set_frame_on(False) # turn off the frame
    ax.set_aspect('equal')
    ax.set_autoscale_on(False)  

    # put the major ticks at the middle of each cell
    ax.set_xticks(np.arange(xdim)+0.5, minor=False)
    ax.set_yticks(np.arange(ydim)+0.5, minor=False)

    # want a more natural, table-like display
    ax.invert_yaxis()
    ax.xaxis.tick_top()

    ax.set_xticklabels(labelsX, minor=False, rotation=90) 
    ax.set_yticklabels(labelsY, minor=False)

    ax.xaxis.set_tick_params(bottom='off', top='off', left='off', right='off')
    ax.yaxis.set_tick_params(bottom='off', top='off', left='off', right='off')

    #fig.tight_layout()

    return fig
