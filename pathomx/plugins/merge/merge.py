import pandas as pd

# Check they are of the same dimensionality
assert len(input_1.shape) == len(input_2.shape)

input_1.shape, input_2.shape

if input_1.shape[0] == input_2.shape[0]:
    # We match on axis 0, go with it
    output_data = pd.concat([input_1, input_2], axis=0)

elif input_1.shape[1] == input_2.shape[1]:
    # We match on axis 1, go with that
    output_data = pd.concat([input_1, input_2], axis=1)

else:
    assert False, "Couldn't find matching dimension"
