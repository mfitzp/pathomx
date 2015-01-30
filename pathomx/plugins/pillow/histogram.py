from PIL import Image
import matplotlib.pyplot as plt
import numpy as np

Histogram = plt.Figure()
ax = Histogram.add_subplot(111)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.get_xaxis().tick_bottom()
ax.get_yaxis().tick_left()

values = np.array( input_image.histogram() ) #mask=None, extrema=None

bands = list( input_image.mode )
values = np.split( values, len(bands))


for b, v in zip(bands, values):
    ax.bar(np.arange(0, len(v) ), v, 1, color=b.lower(), alpha=0.6)
