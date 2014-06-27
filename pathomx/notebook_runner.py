from __future__ import print_function
'''
Broken attempt to implement a QtInProcess version of runipy
'''
try:
    # python 2
    from Queue import Empty
except:
    # python 3
    from queue import Empty

import platform
from time import sleep
import logging
import os

from IPython.nbformat.current import NotebookNode
from IPython.kernel import KernelManager

from IPython.qt.base_frontend_mixin import BaseFrontendMixin

# FIXME: This needs work to handle the InProcessKernelManager
# e.g. the async message handling
from IPython.qt.inprocess import QtInProcessKernelManager

class NotebookError(Exception):
    pass


class NotebookRunner(BaseFrontendMixin):
    # The kernel communicates with mime-types while the notebook
    # uses short labels for different cell types. We'll use this to
    # map from kernel types to notebook format types.

    MIME_MAP = {
        'image/jpeg': 'jpeg',
        'image/png': 'png',
        'text/plain': 'text',
        'text/html': 'html',
        'text/latex': 'latex',
        'application/javascript': 'html',
        'image/svg+xml': 'svg',
    }

    def __init__(self, nb):

        self.km = QtInProcessKernelManager()

        cwd = os.getcwd()

        self.km.start_kernel()
        self.kernel = self.km.kernel
        
        self.kc = self.km.client()
        self.kc.start_channels()

        self.shell = self.kc.shell_channel
        self.shell.message_received.connect( self.shell_message_handler )
        self.shell.complete_reply.connect( self.cell_execute_complete_handler )
        
        self.iopub = self.kc.iopub_channel
        self.iopub.display_data_received.connect( self.iopub_message_handler )
        self.iopub.execute_result_received.connect( self.cell_execute_complete_handler )

        self.nb = nb

    def __del__(self):
        self.kc.stop_channels()
        self.km.shutdown_kernel(now=True)

    def run_cell(self, cell):
        '''
        Run a notebook cell and update the output of that cell in-place.
        '''        
        logging.info('Running cell:\n%s\n', cell.input)
        self.latest_cell_executed = cell
        self.latest_cell_output = []

        self.shell.execute(cell.input)

    def run_next_cell(self):
        print('*********** RUN CELL ************')
        cell = self.notebook_iterator.next()
        print(cell)
        self.run_cell(cell)
        print('*********** RUN CELL ************')
    
        
    def shell_message_handler(self, reply):
        print("[[SHELL MESSAGE]]")
        print(reply)
        status = reply['content']['status']
        if status == 'error':
            traceback_text = 'Cell raised uncaught exception: \n' + \
                '\n'.join(reply['content']['traceback'])
            logging.info(traceback_text)
            raise NotebookError(traceback_text)
        else:
            logging.info('Cell returned')


    def iopub_message_handler(self, msg):
        print("[[IOPUB MESSAGE]]")

        if msg['msg_type'] != 'status' or msg['content']['execution_state'] != 'idle':
            return False

        content = msg['content']
        msg_type = msg['msg_type']

        out = NotebookNode(output_type=msg_type)

        # IPython 3.0.0-dev writes pyerr/pyout in the notebook format but uses
        # error/execute_result in the message spec. This does the translation
        # needed for tests to pass with IPython 3.0.0-dev
        notebook3_format_conversions = {
            'error': 'pyerr',
            'execute_result': 'pyout'
        }
        msg_type = notebook3_format_conversions.get(msg_type, msg_type)

        if 'execution_count' in content:
            cell['prompt_number'] = content['execution_count']
            out.prompt_number = content['execution_count']

        if msg_type in ('status', 'pyin', 'execute_input'):
            return False
            
        elif msg_type == 'stream':
            out.stream = content['name']
            out.text = content['data']
            #print(out.text, end='')
        elif msg_type in ('display_data', 'pyout'):
            for mime, data in content['data'].items():
                try:
                    attr = self.MIME_MAP[mime]
                except KeyError:
                    raise NotImplementedError('unhandled mime type: %s' % mime)

                setattr(out, attr, data)
            #print(data, end='')
        elif msg_type == 'pyerr':
            out.ename = content['ename']
            out.evalue = content['evalue']
            out.traceback = content['traceback']

            #logging.error('\n'.join(content['traceback']))
        elif msg_type == 'clear_output':
            outs = list()
            return False
        else:
            raise NotImplementedError('unhandled iopub message: %s' % msg_type)
            
        self.latest_cell_output.append(out)

    def cell_execute_complete_handler(self):
        self.latest_cell_executed['outputs'] = self.latest_cell_output
        self.run_next_cell()

    def iter_code_cells(self):
        '''
        Iterate over the notebook cells containing code.
        '''
        for ws in self.nb.worksheets:
            for cell in ws.cells:
                if cell.cell_type == 'code':
                    yield cell

    def run_notebook(self, *args, **kwargs):
        self.notebook_iterator = self.iter_code_cells()
        self.run_next_cell()

    def arun_notebook(self, skip_exceptions=False, execute_cell_no_callback=None):
        '''
        Run all the cells of a notebook in order and update
        the outputs in-place.

        If ``skip_exceptions`` is set, then if exceptions occur in a cell, the
        subsequent cells are run (by default, the notebook execution stops).
        '''
        for n, cell in enumerate(self.iter_code_cells()):
            try:
                self.run_cell(cell)
            except NotebookError:
                if not skip_exceptions:
                    raise
            if execute_cell_no_callback:
                execute_cell_no_callback(n)

    def count_code_cells(self):
        '''
        Return the number of code cells in the notebook
        '''
        for n, cell in enumerate(self.iter_code_cells()):
            pass
        return n
