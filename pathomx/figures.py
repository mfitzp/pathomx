# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd

from collections import OrderedDict

from . import utils

# from matplotlib.figure import Figure
from matplotlib.path import Path
from matplotlib.patches import BoxStyle, Ellipse, Rectangle
from matplotlib.transforms import Affine2D, Bbox, BboxBase
import matplotlib.cm as cm

import matplotlib.pyplot as plt

Figure = plt.figure

FIGURE_SIZE = (5, 5)
FIGURE_DPI = 300


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
        width, height = width + 2. * pad, \
                        height + 2. * pad,

        # boundary of the padded box
        x0, y0 = x0 - pad, y0 - pad,
        x1, y1 = x0 + width, y0 + height

        cp = [(x0, y0),
              (x1, y0), (x1, y1), (x0, y1),
              (x0 - pad, (y0 + y1) / 2.), (x0, y0),
              (x0, y0)]

        com = [Path.MOVETO,
               Path.LINETO, Path.LINETO, Path.LINETO,
               Path.LINETO, Path.LINETO,
               Path.CLOSEPOLY]

        path = Path(cp, com)

        return path

# register the custom style
BoxStyle._style_list["entity-tip"] = EntityBoxStyle


def get_text_bbox_screen_coords(fig, t):
    renderer = fig.canvas.get_renderer()
    bbox = t.get_window_extent(renderer)
    return bbox.get_points()


def get_text_bbox_data_coords(fig, ax, t):
    renderer = fig.canvas.get_renderer()
    bbox = t.get_window_extent(renderer)
    axbox = bbox.transformed(ax.transData.inverted())
    return axbox.get_points()


def extend_limits(a, b):
    # Extend a to meet b where applicable
    ax, ay = list(a[0]), list(a[1])
    bx, by = b[:, 0], b[:, 1]
    ax[0] = bx[0] if bx[0] < ax[0] else ax[0]
    ax[1] = bx[1] if bx[1] > ax[1] else ax[1]
    ay[0] = by[0] if by[0] < ay[0] else ay[0]
    ay[1] = by[1] if by[1] > ay[1] else ay[1]
    return [ax, ay]


def find_linear_scale(data):
    scale = []
    scale_name = []
    linear_scale = False
    longest = None
    if type(data.columns) == pd.MultiIndex:
        for n, l in enumerate(data.columns.levels):
            if l.dtype == np.dtype('O'):  # Object; maybe str?
                if len(l) > longest:
                    longest = len(l)

            elif np.issubdtype(l.dtype, np.integer) or np.issubdtype(l.dtype, np.float):
                linear_scale = True
                scale = [v[n] for v in data.columns.values]
                scale_name = data.columns.names[n]

                if np.issubdtype(l.dtype, np.float):
                    # Prefer float scales, assume more accurate
                    break
    else:
        scale = []
        linear_scale = True
        for x in data.columns.values:
            try:
                scale.append(float(x))
            except:
                linear_scale = False
                break

    return scale, linear_scale, scale_name


def spectra(data, figure=None, ax=None, styles=None, regions=None):
    if figure is None:
        figure = Figure(figsize=FIGURE_SIZE, dpi=FIGURE_DPI)

    if ax is None:
        ax = figure.add_subplot(111)

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

    if 'Class' in data.index.names and len(data.index.levels[data.index.names.index('Class')]) > 1:
        class_idx = data.index.names.index('Class')
        classes = list(data.index.levels[class_idx])
    else:
        class_idx = None
        classes = False

    if class_idx is not None and len(classes) > 1:  # We have (more than one) classes

        # More than one data row (class) so plot each class
        # Calculate a mean for each class
        data_mean = data.mean(level=class_idx)
        data_max = data_mean.max()
        data_abs_max = data_mean.abs().max()

    else:
        data_mean = data.mean()
        data_max = data.max()
        data_abs_max = data.abs().max()

    # Annotate using the most non-numeric column index that is most complete
    data_headers = None
    longest_level = None
    longest = None

    linear_scale = False
    linear_scale_idx = None

    scale, linear_scale, scale_name = find_linear_scale(data)

    if longest:
        data_headers = np.array([v[longest_level] for v in data.columns.values])

    # Temporary scale
    if linear_scale:
        scale = np.array(scale)
        is_scale_reversed = scale[0] > scale[-1]
    else:
        scale = np.arange(0, data.shape[1])
        is_scale_reversed = False

    if is_scale_reversed:
        ax.invert_xaxis()

    if classes:

        # More than one data row (class) so plot each class
        # Calculate a mean for each class

        plots = OrderedDict()
        for n, c in enumerate(classes):
            if styles:
                ls = styles.get_style_for_class(c).line_kwargs
            else:
                ls = {}

            row = data_mean.ix[c]
            plots[c], = ax.plot(scale, row, **ls)

        legend = ax.legend(list(plots.values()),
                           list(plots.keys()),
                           loc='best')  #, bbox_to_anchor=(1, 1))
        legend.get_frame().set_facecolor('k')
        legend.get_frame().set_alpha(0.05)

    else:
        # Only one data row (class) so plot individual data; with a mean line
        data_mean = np.mean(data, axis=0)
        data_individual = data

        for n in range(0, data_individual.shape[0]):
            row = data_individual.iloc[n]

            ax.plot(scale, row.values, linewidth=0.75, alpha=0.25, color=utils.category10[0])

        ax.plot(scale, data_mean.values, linewidth=0.75, color=utils.category10[0])

    axlimits = ( ax.get_xlim(), ax.get_ylim() )

    if data_headers is not None:
        mask = np.isnan(data_abs_max)
        data_abs_max_ma = np.ma.masked_array(data_abs_max, mask=mask)
        idx = list(np.argsort(data_abs_max_ma))[-10:]

        anno_label = data_headers[idx]
        anno_scale = scale[idx]
        anno_y = data_max[idx]

        for x, y, l in zip(anno_scale, anno_y, anno_label):
            print "*", x, y, l
            if y >= 0:
                r = '60'
            else:
                r = '-60'
            if l:
                t = ax.text(x, y, l, rotation=r, rotation_mode='anchor', size=6.5,
                            bbox=dict(boxstyle="round,pad=0.1", fc="#eeeeee", ec="none"))
                bounds = get_text_bbox_data_coords(figure, ax, t)
                if y >= 0:
                    bounds[1, 1] = bounds[1, 1] * 1.25
                else:
                    bounds[0, 1] = bounds[0, 1] * 1.25

                axlimits = extend_limits(axlimits, bounds)

        #ax.set_xlim( axlimits[0] )
        ax.set_ylim(axlimits[1])

    if scale_name:
        ax.set_xlabel(scale_name)


    if regions:  # Plot defined x0, y0, x1, y2 regions onto the plot
        for x0, y0, x1, y1 in regions:
            ax.add_patch( Rectangle( (x0, y0), x1-x0, y1-y0, facecolor="grey", alpha=0.3))

    return figure


def category_bar(data, figure=None, styles=None):
    if figure is None:
        figure = Figure(figsize=FIGURE_SIZE, dpi=FIGURE_DPI)

    if ax is None:
        ax = figure.add_subplot(111)

    ax = figure.axes[0]
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.get_xaxis().tick_bottom()
    ax.get_yaxis().tick_left()

    if data is None:
        assert False

    # Build x positions; we're grouping by X (entity) then plotting the classes
    ax.cla()

    limit_to = 10

    # FIXME: Remove this once UI allows selection of data to plot
    fd = np.mean(dso.data, axis=0)
    fdm = list(zip(dso.labels[1], fd))
    sms = sorted(fdm, key=lambda x: abs(x[1]), reverse=True)
    labels = [m for m, s in sms]

    plots = OrderedDict()
    classes = dso.classes[0]
    #labels = [e if e is not None else dso.labels[1][n] for n,e in enumerate(dso.entities[1][0:limit_to]) ]
    #data = dso.data[:,0:limit_to]
    data = np.array([dso.data[:, dso.labels[1].index(l)] for l in labels]).T[:, :limit_to]

    #0,1,-,4,5,-,6,7

    # 2 classes
    # 3 data points

    # 3*2 = 6;  3*(2+1) = 9

    # Build spaced sets (around middle value)
    # 0 -0.5->+0.5, 

    xa = []
    for n, ag in enumerate(data.T):  # Axis groups (can reverse with classes; later)
        xa.append(np.arange(0, len(classes)) + n * (len(classes) + 1))  # Build table

    x = np.array(xa).reshape(len(data.T), len(classes))

    ax.set_xlim(np.min(x) - 1, np.max(x) + 1)

    for n, c in enumerate(classes):
        cdata = data[n]
        if 'error' in dso.statistics:
            err = dso.statistics['error']['stddev'][:, :limit_to][n]
            yperr = [(0, 1)[e > 0] for e in cdata]
            ynerr = [(0, 1)[e < 0] for e in cdata]

            yperr = np.array(yperr) * err
            ynerr = np.array(ynerr) * err
            yerr = (ynerr, yperr)
        else:
            yerr = None

        ls = styles.get_style_for_class(c)
        plots[c] = self.ax.bar(x[:, n], cdata, align='center', yerr=yerr, **ls.bar_kwargs)

    xticks = np.mean(x, axis=1)
    ax.set_xticks(xticks)
    ax.set_xticklabels(labels, rotation=45, ha='right', rotation_mode='anchor')

    legend = self.ax.legend(list(plots.values()),
                            list(plots.keys()),
                            loc='best')  #, bbox_to_anchor=(1, 1))
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


# Add ellipses for confidence intervals, with thanks to Joe Kington
# http://stackoverflow.com/questions/12301071/multidimensional-confidence-intervals
def plot_point_cov(points, nstd=2, **kwargs):
    """
    Plots an `nstd` sigma ellipse based on the mean and covariance of a point
    "cloud" (points, an Nx2 array).

    Parameters
    ----------
        points : An Nx2 array of the data points.
        nstd : The radius of the ellipse in numbers of standard deviations.
            Defaults to 2 standard deviations.
        Additional keyword arguments are pass on to the ellipse patch.

    Returns
    -------
        A matplotlib ellipse artist
    """
    pos = points.mean(axis=0)
    cov = np.cov(points, rowvar=False)
    return plot_cov_ellipse(cov, pos, nstd, **kwargs)


def plot_cov_ellipse(cov, pos, nstd=2, **kwargs):
    """
    Plots an `nstd` sigma error ellipse based on the specified covariance
    matrix (`cov`). Additional keyword arguments are passed on to the 
    ellipse patch artist.

    Parameters
    ----------
        cov : The 2x2 covariance matrix to base the ellipse on
        pos : The location of the center of the ellipse. Expects a 2-element
            sequence of [x0, y0].
        nstd : The radius of the ellipse in numbers of standard deviations.
            Defaults to 2 standard deviations.
        Additional keyword arguments are pass on to the ellipse patch.

    Returns
    -------
        A matplotlib ellipse artist
    """

    def eigsorted(cov):
        vals, vecs = np.linalg.eigh(cov)
        order = vals.argsort()[::-1]
        return vals[order], vecs[:, order]

    vals, vecs = eigsorted(cov)
    theta = np.degrees(np.arctan2(*vecs[:, 0][::-1]))

    # Width and height are "full" widths, not radius
    width, height = 2 * nstd * np.sqrt(vals)
    ellip = Ellipse(xy=pos, width=width, height=height, angle=theta, fill=False, **kwargs)

    return ellip


def scatterplot(data, figure=None, ax=None, styles=None, lines=[], label_index=None):
    if figure is None:
        figure = Figure(figsize=FIGURE_SIZE, dpi=FIGURE_DPI)

    if ax is None:
        ax = figure.add_subplot(111)

    ax = figure.axes[0]
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.get_xaxis().tick_bottom()
    ax.get_yaxis().tick_left()

    ax.cla()

    if data is None:
        assert False

    if 'Class' in data.index.names and len(data.index.levels[data.index.names.index('Class')]) > 1:
        class_idx = data.index.names.index('Class')
        classes = list(data.index.levels[class_idx])
    else:
        class_idx = None
        classes = [None]

    plots = OrderedDict()
    for c in classes:
        if styles:
            ls = styles.get_style_for_class(c)
        else:
            ls = None

        if c is not None:
            df = data.xs(c, level=class_idx)
        else:
            df = data

        s = ls.markersize ** 2 if ls.markersize is not None else 20  #default
        plots[c] = ax.scatter(df.iloc[:, 0].values, df.iloc[:, 1].values, color=ls.markerfacecolor, marker=ls.marker, s=s)


        # Calculate 95% confidence interval for data but only if points >1
        if df.values.shape[0] > 1:
            ellip = plot_point_cov(df.values, nstd=2, linestyle='dashed', linewidth=0.5, edgecolor=ls.color,
                                   alpha=0.5)  #**kwargs for ellipse styling
            ax.add_artist(ellip)

    # If overlay lines are defined; plot + annotation           
    for x, y, label in lines:
        ls = styles.get_style_for_class(None)  # Blank for now; need to replace with general 'info lines' settings
        ax.plot(x, y, **ls.line_kwargs)
        ax.annotate(label, xy=(x[-1], y[-1]))

    if len(plots.keys()) > 1:
        # Only show a legend if there is >1 class (?)
        legend = ax.legend(list(plots.values()),
                           list(plots.keys()),
                           scatterpoints=1,
                           loc='upper left', bbox_to_anchor=(1, 1))
        legend.get_frame().set_facecolor('k')
        legend.get_frame().set_alpha(0.05)

        #ax.set_xlabel(dso.labels[1][0])
    #ax.set_ylabel(dso.labels[1][1])

    # Square the plot
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    ax.set_aspect((x1 - x0) / (y1 - y0))

    if label_index is not None and label_index in data.index.names:
        idx = data.index.names.index(label_index)
        labels = [v[idx] for v in data.index.values]
        for label, x, y in zip(labels, data.iloc[:, 0], data.iloc[:, 1]):
            ax.annotate(label, xy=(x, y), xytext=(-1, 1), textcoords='offset points', ha='right', va='bottom',
                        size='small')

    return figure


def heatmap(data, figure=None, ax=None, styles=None):
    if figure is None:
        figure = Figure(figsize=FIGURE_SIZE, dpi=FIGURE_DPI)

    if ax is None:
        ax = figure.add_subplot(111)

    ylim = np.abs(data.max().max())


    # Plot it out
    datav = np.float64(data.values.T)
    log2data = np.log2(datav)

    ax.imshow(log2data, interpolation='none', aspect='auto', cmap=cm.RdBu_r)  # vmin=-ylim, vmax=+ylim, )
    # turn off the frame
    ax.set_frame_on(False)

    labels_x = [v[data.index.names.index('Class')] for v in data.index.values]
    # print labels_x
    ax.set_xticklabels(labels_x, minor=False)
    ax.set_xticks(np.arange(len(labels_x)), minor=False)
    ax.xaxis.tick_top()

    '''
    # put the major ticks at the middle of each cell
    ax.set_yticks(np.arange(data.values.shape[0])+0.5, minor=False)

    # want a more natural, table-like display
    
    # Set the labels

    # note I could have used nba_sort.columns but made "labels" instead
    labels_x = [ v[ data.columns.names.index('Label') ] for v in data.columns.values]
    ax.set_xticklabels(labels_x, minor=False) 

    # rotate the 
    plt.xticks(rotation=90)

    for t in ax.xaxis.get_major_ticks(): 
        t.tick1On = False 
        t.tick2On = False 
    for t in ax.yaxis.get_major_ticks(): 
        t.tick1On = False 
        t.tick2On = False    
    '''
    ax.grid(False)

    return figure



def difference(data1, data2, figure=None, ax=None, styles=None):
    if figure is None:
        figure = Figure(figsize=FIGURE_SIZE, dpi=FIGURE_DPI)

    if ax is None:
        ax = figure.add_subplot(111)

    ax = figure.axes[0]
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.get_xaxis().tick_bottom()
    ax.get_yaxis().tick_left()
    ax.cla()

    # Get common scales
    data1v = np.mean(data1.values, 0)  # Mean flatten
    data2v = np.mean(data2.values, 0)  # Mean flatten

    scale1, linear_scale1, scale_name1 = find_linear_scale(data1)
    scale2, linear_scale2, scale_name2 = find_linear_scale(data2)

    if not linear_scale1 or not linear_scale2:
        return None # Can't interpolate with non-linear scale

    is_reversed = False

    scale1 = np.array(scale1)
    scale2 = np.array(scale2)

    if scale1[0] > scale1[-1]:
        # Reverse direction
        is_reversed = True
        # Flip to increasing for interpolation
        scale1 = scale1[::-1]
        data1v = data1v[::-1]

    if scale2[0] > scale2[-1]:
        scale2 = scale2[::-1]
        data2v = data2v[::-1]

    # Interpolate the data for shorter set
    if len(scale1) < len(scale2):
        data1v = np.interp(np.array(scale2), np.array(sorted(scale1)), data1v)
        x = scale2

    elif len(scale1) > len(scale2):
        data2v = np.interp(np.array(scale1), np.array(sorted(scale2)), data2v)
        x = scale1

    else:
        x = scale1

    # Return to original order (not we must sort both arrays the same direction)
    if is_reversed:
        x = x[::-1]
        data1v = data1v[::-1]
        data2v = data2v[::-1]

    y1 = data1v
    y2 = data2v

    ax.cla()
    ax.plot(x, y2, color='black', linewidth=0.25)
    ax.fill_between(x, y1, y2, where=y2 >= y1, facecolor=utils.category10[0], interpolate=False)
    ax.fill_between(x, y1, y2, where=y2 <= y1, facecolor=utils.category10[1], interpolate=False)

    if scale_name1:
        ax.set_xlabel(scale_name1)

    return figure
