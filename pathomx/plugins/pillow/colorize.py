from PIL import ImageOps
from pathomx.utils import hexrgb

input_image = input_image.convert(mode='L')
output_image = ImageOps.colorize(input_image, hexrgb(config.get('black'), scale=255), hexrgb(config.get('white'), scale=255), )
output_image = output_image.convert(mode='RGB')
