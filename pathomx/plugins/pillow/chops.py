from PIL import ImageChops

# Currently supported modes include:
# add_modulo, darker, difference, lighter, logical_and, logical_or, multiple, screen, subtract_modulo

op = config.get('operation')

if op == 'add_modulo':
    output_image = ImageChops.add_modulo(image1, image2)

elif op == 'darker':
    output_image = ImageChops.darker(image1, image2)

elif op == 'difference':
    output_image = ImageChops.difference(image1, image2)

elif op == 'lighter':
    output_image = ImageChops.lighter(image1, image2)

elif op == 'logical_and':
    output_image = ImageChops.logical_and(image1, image2)

elif op == 'logical_or':
    output_image = ImageChops.logical_or(image1, image2)

elif op == 'multiply':
    output_image = ImageChops.multiply(image1, image2)

elif op == 'screen':
    output_image = ImageChops.screen(image1, image2)

elif op == 'subtract_modulo':
    output_image = ImageChops.subtract_modulo(image1, image2)

