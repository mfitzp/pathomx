import os
if config['filename'] is not None:
    path, ext = os.path.splitext(config['filename'])

    if ext in ['.txt', '.csv', '.tsv']:
        input_data.to_csv(config['filename'])

    elif ext in ['.hdf', '.h4', '.hdf4', '.he2', '.h5', '.hdf5', '.he5']:
        input_data.to_hdf(config['filename'])

    elif ext in ['.pickle']:
        input_data.to_pickle(config['filename'])

    elif ext in ['.json']:
        input_data.to_json(config['filename'])
