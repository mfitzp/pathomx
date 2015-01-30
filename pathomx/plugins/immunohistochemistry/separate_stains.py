from PIL import Image
from skimage.color import (combine_stains, separate_stains)
from skimage import color
import numpy as np

STAIN_FN = {
    'hed_from_rgb': (color.hed_from_rgb, color.rgb_from_hed,),
    'hdx_from_rgb': (color.hdx_from_rgb, color.rgb_from_hdx,),
    'fgx_from_rgb': (color.fgx_from_rgb, color.rgb_from_fgx,),
    'bex_from_rgb': (color.bex_from_rgb, color.rgb_from_bex,),
    'rbd_from_rgb': (color.rbd_from_rgb, color.rgb_from_rbd,),
    'gdx_from_rgb': (color.gdx_from_rgb, color.rgb_from_gdx),
    'hax_from_rgb': (color.hax_from_rgb, color.rgb_from_hax),
    'bro_from_rgb': (color.bro_from_rgb, color.rgb_from_bro),
    'bpx_from_rgb': (color.bpx_from_rgb, color.rgb_from_bpx),
    'ahx_from_rgb': (color.ahx_from_rgb, color.rgb_from_ahx),
    'hpx_from_rgb': (color.hpx_from_rgb, color.rgb_from_hpx),
}

STAIN_OUTPUTS = {
    'hed_from_rgb': ('Hematoxylin', 'Eosin', 'DAB'),
    'hdx_from_rgb': ('Hematoxylin', 'DAB'),
    'fgx_from_rgb': ('Feulgen', 'LightGreen'),
    'bex_from_rgb': ('MethylBlue', 'Eosin'),
    'rbd_from_rgb': ('FastRed', 'FastBlue', 'DAB'),
    'gdx_from_rgb': ('MethylGreen', 'DAB'),
    'hax_from_rgb': ('Hematoxylin', 'AEC'),
    'bro_from_rgb': ('AnillineBlue', 'Azocarmine', 'OrangeG'),
    'bpx_from_rgb': ('MethylBlue', 'PonceauFuchsin'),
    'ahx_from_rgb': ('AlcianBlue', 'Hematoxylin'),
    'hpx_from_rgb': ('Hematoxylin', 'PAS'),
}

data = np.array(input_image)
result = separate_stains(data, STAIN_FN[ config['stain'] ][0])

# Gets the first three letters of the config stain key, and strips of the x, then uppercases
# e.g. hed_from_rgb will produce ['H','E','D'] while hdx_from_rgb will produce ['H','D']
outputs = config['stain'].split('_')[0].strip('x').upper()

# Result is the input data mapped into the stain colourspace. This means each slice [:,:,N] contains
# a segment of the data. Take each slice and re-map it individually into RGB as a separate image.
# output_image = Image.fromarray(resultA, mode='RGB')

for n,k in enumerate(outputs):
    tmp = np.zeros( result.shape )
    tmp[:,:,0] = np.min(result[:,:,0]) # White value in this colorspace
    tmp[:,:,1] = np.min(result[:,:,1]) # White value in this colorspace
    tmp[:,:,2] = np.min(result[:,:,2]) # White value in this colorspace

    tmp[:,:,n] = result[:,:,n] # Copy single slice

    islice = combine_stains(tmp, STAIN_FN[ config['stain'] ][1])*255.0
    islice = islice.astype(np.uint8)

    vars()[ STAIN_OUTPUTS[ config['stain'] ][n] ] = Image.fromarray(islice, mode='RGB')
