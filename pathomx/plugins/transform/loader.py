# -*- coding: utf-8 -*-
import pathomx.ui as ui

from pathomx.tools import BaseTool
from pathomx.plugins import ProcessingPlugin
from pathomx.data import DataDefinition


class TransformApp(BaseTool):

    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}

    def __init__(self, *args, **kwargs):
        super(TransformApp, self).__init__(*args, **kwargs)

        self.data.add_input('input_data')  # Add input slot
        self.data.add_output('output_data')  # Add output slot

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input_data', {  # Accept anything!
            })
        )


class TransformMeanCenter(TransformApp):
    name = "Mean Center"
    notebook = 'mean_center.ipynb'
    shortname = 'mean_center'


class TransformLog2(TransformApp):
    name = "Log2"
    notebook = 'log2.ipynb'
    shortname = 'log2'


class TransformLog10(TransformApp):
    name = "Log10"
    notebook = 'log10.ipynb'
    shortname = 'log10'


class TransformZeroBaseline(TransformApp):
    name = "Zero baseline"
    notebook = 'zero_baseline.ipynb'
    shortname = 'zero_baseline'


class TransformGlobalMinima(TransformApp):
    name = "Global minima"
    notebook = 'global_minima.ipynb'
    shortname = 'global_minima'


class TransformLocalMinima(TransformApp):
    name = "Local minima"
    notebook = 'local_minima.ipynb'
    shortname = 'local_minima'


class TransformRemoveInvalid(TransformApp):
    name = "Remove invalid data"
    notebook = 'remove_invalid.ipynb'
    shortname = 'remove_invalid'


class TransformTranspose(TransformApp):
    name = "Transpose"
    notebook = 'transpose.ipynb'
    shortname = 'transpose'


class TransformSplitImaginary(BaseTool):
    name = "Split real/imaginary numbers"
    notebook = 'split_imaginary.ipynb'
    shortname = 'split_imaginary'

    def __init__(self, *args, **kwargs):
        super(TransformSplitImaginary, self).__init__(*args, **kwargs)

        self.data.add_input('input_data')  # Add input slot

        self.data.add_output('real')
        self.data.add_output('imag')

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input_data', {  # Accept anything!
            })
        )


class Transform(ProcessingPlugin):

    def __init__(self, *args, **kwargs):
        super(Transform, self).__init__(*args, **kwargs)
        self.register_app_launcher(TransformMeanCenter)
        self.register_app_launcher(TransformLog2)
        self.register_app_launcher(TransformLog10)
        self.register_app_launcher(TransformZeroBaseline)
        self.register_app_launcher(TransformGlobalMinima)
        self.register_app_launcher(TransformLocalMinima)
        self.register_app_launcher(TransformRemoveInvalid)
        self.register_app_launcher(TransformTranspose)
        self.register_app_launcher(TransformSplitImaginary)
