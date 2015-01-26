from PIL import Image

output_image = Image.open(config['filename'])
output_image.load()

if config.get('colorspace'):
    output_image = output_image.convert(mode=config.get('colorspace'))

