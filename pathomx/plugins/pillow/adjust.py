from PIL import ImageEnhance

output_image = input_image

if config.get('brightness') != 100:
    adjuster = ImageEnhance.Brightness(output_image)
    output_image = adjuster.enhance(float(config.get('brightness')) / 100)

if config.get('contrast') != 100:
    adjuster = ImageEnhance.Contrast(output_image)
    output_image = adjuster.enhance(float(config.get('contrast')) / 100)

if config.get('color') != 100:
    adjuster = ImageEnhance.Color(output_image)
    output_image = adjuster.enhance(float(config.get('color')) / 100)

if config.get('sharpness') != 100:
    adjuster = ImageEnhance.Sharpness(output_image)
    output_image = adjuster.enhance(float(config.get('sharpness')) / 100)
