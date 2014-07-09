import logging

from collections import namedtuple

from IPython.nbformat.current import NotebookNode
from IPython.nbconvert.exporters import export as IPyexport
from IPython.nbconvert.exporters.export import exporter_map as IPyexporter_map
from IPython.qt.base_frontend_mixin import BaseFrontendMixin

from .qt import *

if USE_QT_PY == PYQT5:
    # The normal ZMQ kernel doesn't work in PyQt5 yet so use in the in-process one
    from IPython.qt.inprocess import QtInProcessKernelManager as KernelManager
    MAX_RUNNER_QUEUE = 1 # In process; can only have one

else:
    # In PyQt4 we can use the ZMQ kernel and avoid blocking
    from IPython.qt.manager import QtKernelManager as KernelManager
    MAX_RUNNER_QUEUE = 3 # Multi-threaded; but most processing is linear 3-5 good max

try:
    # For depickling we can use cPickle even if pickled with dill
    import cPickle as pickle
except:
    import pickle
    
import uuid
from copy import deepcopy
from datetime import datetime


class NotebookRunner(BaseFrontendMixin, QObject):
    '''
    A runner object that handles running the running of IPython notebook and working
    responses back into the output notebook. Based off the original runipy code
    amended to handle in-process running and the IPython FrontendWidget.
    '''

    # Emitted when a user visible 'execute_request' has been submitted to the
    # kernel from the FrontendWidget. Contains the code to be executed.
    executing = pyqtSignal(object)

    # Emitted when a user-visible 'execute_reply' has been received from the
    # kernel and processed by the FrontendWidget. Contains the response message.
    executed = pyqtSignal(object)

    # Emitted when an exit request has been received from the kernel.
    exit_requested = pyqtSignal(object)

    # Execute next cell
    execute_next = pyqtSignal()
    
    # Emitted when all cells a notebook have been run
    notebook_completed = pyqtSignal()
    notebook_result = pyqtSignal(object)
    
    # Emit current cell number
    progress = pyqtSignal(object)

    _CallTipRequest = namedtuple('_CallTipRequest', ['id', 'pos'])
    _CompletionRequest = namedtuple('_CompletionRequest', ['id', 'pos'])
    _ExecutionRequest = namedtuple('_ExecutionRequest', ['id', 'kind'])
    _local_kernel = False
    _hidden = False
    
    MIME_MAP = {
        'image/jpeg': 'jpeg',
        'image/png': 'png',
        'text/plain': 'text',
        'text/html': 'html',
        'text/latex': 'latex',
        'application/javascript': 'html',
        'image/svg+xml': 'svg',
    }    

    #---------------------------------------------------------------------------
    # 'object' interface
    #---------------------------------------------------------------------------

    def __init__(self, *args, **kwargs):
        super(NotebookRunner, self).__init__(*args, **kwargs)
        # FrontendWidget protected variables.
        self._kernel_manager = None
        self._kernel_client = None
        self._request_info = {}
        self._request_info['execute'] = {};
        self._callback_dict = {}
        
        self._result_queue = []
        self._final_msg_id = None
        self._cell_execute_ids = {}
        
        self._is_active = False
        self._executing = False
        
        # Set flag for whether we are connected via localhost.
        self._local_kernel = kwargs.get('local_kernel',
                                    NotebookRunner._local_kernel)

        self.kernel_manager = KernelManager()
        self.kernel_manager.start_kernel()

        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels(stdin=False, hb=False)

    def __del__(self):
        if self.kernel_client:
            self.kernel_client.stop_channels()
        if self.kernel_manager:
            self.kernel_manager.shutdown_kernel()

    def iter_code_cells(self):
        '''
        Iterate over the notebook cells containing code.
        '''
        for ws in self.nb.worksheets:
            for cell in ws.cells:
                if cell.cell_type == 'code':
                    yield cell

    def count_code_cells(self):
        '''
        Return the number of code cells in the notebook
        '''
        for n, cell in enumerate(self.iter_code_cells()):
            pass
        return n+1

    def run_notebook(self, notebook, varsi, progress_callback=None, result_callback=None):
        '''
        Run all the cells of a notebook in order and update
        the outputs in-place.
        '''
        
        self.nb = notebook
        self.varsi = varsi
        # Pickle all variables and import to the notebook (depickler)
        with open(self.varsi['_pathomx_pickle_in'], 'wb') as f:
            pickle.dump(self.varsi, f, -1)  # Highest protocol for speed
        
        self._progress_callback = progress_callback
        self._result_callback = result_callback
        self._notebook_generator = self.iter_code_cells()

        self._total_code_cell_number = self.count_code_cells()
        self._is_active = True

        self._result_queue = [] # Cache for unhandled messages
        self._cell_execute_ids = {}
        self._execute_start = datetime.now()

        msg_id = self._execute('''%%reset -f
from pathomx import pathomx_notebook_start, pathomx_notebook_stop
pathomx_notebook_start('%s', vars());''' % (self.varsi['_pathomx_pickle_in'])
)       
        logging.debug("Runing notebook; startup message: %s" % msg_id)
        for n, cell in enumerate(self.iter_code_cells()):
            msg_id = self._execute(cell.input)
            logging.debug('Cell number %d; %s' % ( n, msg_id) )
            progress = n / float(self._total_code_cell_number)            
            self._cell_execute_ids[ msg_id ] = (cell, n+1, progress) # Store cell and progress

        self._final_msg_id = self._execute('''pathomx_notebook_stop('%s', vars());''' % (self.varsi['_pathomx_pickle_out']))       
        logging.debug("Runing notebook; shutdown message: %s" % self._final_msg_id)

    def run_notebook_completed(self, error=False, traceback=None):
        logging.info("Notebook run took %s" % ( datetime.now() - self._execute_start ) )
        result = {}
        if error:
            result['status'] = -1
            result['traceback'] = traceback
        else:
            # Apply unhandled results
            for msg in self._result_queue:
                self._handle_execute_result(msg)
        
            result['status'] = 0
            # Return input; temp
            with open(self.varsi['_pathomx_pickle_out'], 'rb') as f:
                result['varso'] = pickle.load(f)

        result['notebook'] = self.nb

        self._is_active = False
        self.notebook_completed.emit()
        self.notebook_result.emit(result)
        if self._result_callback:
            self._result_callback(result)
    

    def _execute(self, source, hidden=False):
        """ Execute 'source'. If 'hidden', do not show any output.

        See parent class :meth:`execute` docstring for full details.
        """
        msg_id = self.kernel_client.execute(source, hidden)
        self._request_info['execute'][msg_id] = self._ExecutionRequest(msg_id, 'user')
        self._hidden = hidden
        #if not hidden:
        #    self.executing.emit(source)
        return msg_id

    #---------------------------------------------------------------------------
    # 'BaseFrontendMixin' abstract interface
    #---------------------------------------------------------------------------
    def _handle_clear_output(self, msg):
        """Handle clear output messages."""
        if not self._hidden and self._is_from_this_session(msg):
            wait = msg['content'].get('wait', True)
            if wait:
                self._pending_clearoutput = True
            else:
                self.clear_output()


    def _handle_execute_reply(self, msg):
        """ Handles replies for code execution.
        """
        logging.debug("execute: %s", msg.get('content', ''))
        msg_id = msg['parent_header']['msg_id']
        
        if msg_id == self._final_msg_id:
            return self.run_notebook_completed()
            
        if msg_id not in self._cell_execute_ids:
            return

        
        (self._current_cell, n, pc) = self._cell_execute_ids[msg_id]

        logging.info("Execute cell %d complete in %s" % (n, datetime.now() - self._execute_start) )
               
        
        self.progress.emit( pc )
        if self._progress_callback:
            self._progress_callback( pc )
    
        info = self._request_info['execute'].get(msg_id)
        # unset reading flag, because if execute finished, raw_input can't
        # still be pending.
        self._reading = False

        if info and info.kind == 'user' and not self._hidden:
            # Make sure that all output from the SUB channel has been processed
            # before writing a new prompt.
            self.kernel_client.iopub_channel.flush()

            # Reset the ANSI style information to prevent bad text in stdout
            # from messing up our colors. We're not a true terminal so we're
            # allowed to do this.
            # if self.ansi_codes:
            #     self._ansi_processor.reset_sgr()

            content = msg['content']
            status = content['status']
            if status == 'ok':
                self._process_execute_ok(msg)
                self.execute_next.emit()
            elif status == 'error':
                self._process_execute_error(msg)
            elif status == 'aborted':
                self._process_execute_abort(msg)

            self.executed.emit(msg)
            self._request_info['execute'].pop(msg_id)
        elif info and info.kind == 'silent_exec_callback' and not self._hidden:
            self._handle_exec_callback(msg)
            self._request_info['execute'].pop(msg_id)
        else:
            super(FrontendWidget, self)._handle_execute_reply(msg)
    
    def _process_execute_abort(self, msg):
        """ Process a reply for an aborted execution request.
        """
        logging.error("ERROR: execution aborted\n")

    def _process_execute_error(self, msg):
        """ Process a reply for an execution request that resulted in an error.
        """
        content = msg['content']
        # If a SystemExit is passed along, this means exit() was called - also
        # all the ipython %exit magic syntax of '-k' to be used to keep
        # the kernel running
        if content['ename']=='SystemExit':
            keepkernel = content['evalue']=='-k' or content['evalue']=='True'
            self._keep_kernel_on_exit = keepkernel
            self.exit_requested.emit(self)
        else:
            traceback = ''.join(content['traceback'])
            logging.info(traceback)
            out = NotebookNode(output_type='pyerr')
            out.ename = content['ename']
            out.evalue = content['evalue']
            out.traceback = content['traceback']
            self._current_cell['outputs'].append(out)
            self.run_notebook_completed(error=True, traceback=content['traceback'])

    def _process_execute_ok(self, msg):
        """ Process a reply for a successful execution request.
        """
        payload = msg['content']['payload']
        for item in payload:
            if not self._process_execute_payload(item):
                warning = 'Warning: received unknown payload of type %s'
                print(warning % repr(item['source']))    
    
        content = msg['content']
        msg_type = msg['msg_type']

        # IPython 3.0.0-dev writes pyerr/pyout in the notebook format but uses
        # error/execute_result in the message spec. This does the translation
        # needed for tests to pass with IPython 3.0.0-dev
        notebook3_format_conversions = {
            'error': 'pyerr',
            'execute_result': 'pyout'
        }
        msg_type = notebook3_format_conversions.get(msg_type, msg_type)
        out = NotebookNode(output_type=msg_type)

        if 'execution_count' in content:
            self._current_cell['prompt_number'] = content['execution_count']
            out.prompt_number = content['execution_count']

        if msg_type in ('status', 'pyin', 'execute_input'):
            return

        elif msg_type == 'stream':
            out.stream = content['name']
            out.text = content['data']

        elif msg_type in ('display_data', 'pyout'):
            # Is this handled in _handle_execute_result?
            for mime, data in content['data'].items():
                try:
                    attr = self.MIME_MAP[mime]
                except KeyError:
                    raise NotImplementedError('unhandled mime type: %s' % mime)

                setattr(out, attr, data)
            return

        elif msg_type == 'pyerr':
            # Is this handled in _handle_execute_errror?
            out.ename = content['ename']
            out.evalue = content['evalue']
            out.traceback = content['traceback']
            return 

        elif msg_type == 'clear_output':
            self._current_cell['outputs'] = []
            return

        elif msg_type == 'execute_reply':
            pass

        else:
            raise NotImplementedError('unhandled iopub message: %s' % msg_type)

        self._current_cell['outputs'].append(out)

    def _handle_kernel_died(self, since_last_heartbeat):
        """Handle the kernel's death (if we do not own the kernel).
        """
        logging.warn("kernel died")
        self.reset()

    def _handle_kernel_restarted(self, died=True):
        """Notice that the autorestarter restarted the kernel.

        There's nothing to do but show a message.
        """
        logging.warn("kernel restarted")
        self.reset()

    def _handle_execute_result(self, msg):
        """ Handle display hook output.
        """

        logging.debug("execute_result: %s", msg.get('content', ''))
        if not self._hidden and self._is_from_this_session(msg):
            msg_id = msg['parent_header']['msg_id']

            if msg_id not in self._cell_execute_ids: # Only on the in-process kernel can this happen
                self._result_queue.append(msg)
                return
                 
            (cell, n, pc) = self._cell_execute_ids[msg_id]

            out = NotebookNode(output_type='display_data')
            for mime, data in msg['content']['data'].items():
                try:
                    attr = self.MIME_MAP[mime]
                except KeyError:
                    raise NotImplementedError('unhandled mime type: %s' % mime)

                setattr(out, attr, data)            
            
            cell['outputs'].append(out)

    def _handle_stream(self, msg):
        """ Handle stdout, stderr, and stdin.
        """
        logging.debug("stream: %s", msg.get('content', ''))
        if not self._hidden and self._is_from_this_session(msg):
            logging.info(msg['content']['data'])

    def _handle_shutdown_reply(self, msg):
        """ Handle shutdown signal, only if from other console.
        """
        logging.info("shutdown: %s", msg.get('content', ''))
        restart = msg.get('content', {}).get('restart', False)
        if not self._hidden and not self._is_from_this_session(msg):
            # got shutdown reply, request came from session other than ours
            if restart:
                # someone restarted the kernel, handle it
                self._handle_kernel_restarted(died=False)
            else:
                # kernel was shutdown permanently
                self.exit_requested.emit(self)

    def _handle_status(self, msg):
        """Handle status message"""
        # This is where a busy/idle indicator would be triggered,
        # when we make one.
        state = msg['content'].get('execution_state', '')
        if state == 'starting':
            # kernel started while we were running
            if self._executing:
                self._handle_kernel_restarted(died=True)
        elif state == 'idle':
            pass
        elif state == 'busy':
            pass

    #---------------------------------------------------------------------------
    # 'FrontendWidget' public interface
    #---------------------------------------------------------------------------

    def interrupt_kernel(self):
        """ Attempts to interrupt the running kernel.
        
        Also unsets _reading flag, to avoid runtime errors
        if raw_input is called again.
        """
        self._reading = False
        self.kernel_manager.interrupt_kernel()

    def restart_kernel(self, message, now=False):
        """ Attempts to restart the running kernel.
        """
        # Pause the heart beat channel to prevent further warnings.
        self.kernel_client.hb_channel.pause()
        try:
            self.kernel_manager.restart_kernel(now=now)
        except RuntimeError as e:
            logging.error('Error restarting kernel: %s\n' % e)
        else:
            logging.info("Restarting kernel...\n")


class NotebookRunnerQueue(QObject):
    '''
    Auto-creating and managing distribution of notebook runners for notebooks.
    Re-population handled on timer. Keeping a maximum N available at all times.
    '''

    start = pyqtSignal()

    def __init__(self, no_of_runners=MAX_RUNNER_QUEUE):
        super(NotebookRunnerQueue, self).__init__() 
        # If we fall beneath the minimum top it up
        self.no_of_runners = no_of_runners
        self.runners = []
        self.active_runners = []
        self.no_of_active_runners = 0

        self.jobs = []  # Job queue a tuple of (notebook, success_callback, error_callback)

        self.start.connect(self.run)

    def start_timers(self):
        self._run_timer = QTimer()
        self._run_timer.timeout.connect(self.run)
        self._run_timer.start(5000)  # Auto-check for pending jobs every 5 seconds; this shouldn't be needed but some jobs get stuck(?)

    def add_job(self, nb, varsi, progress_callback=None, result_callback=None):
        # We take a copy of the notebook, so changes aren't applied back to the source
        # ensuring each run starts with blank slate
        self.jobs.append(( deepcopy(nb), varsi, progress_callback, result_callback))
        self.start.emit() # Auto-start on every add job

    def run(self):
        # Check for jobs
        if not self.jobs:
            return False

        try:
            runner = self.runners.pop(0)  # Remove from the beginning
        except IndexError:
            # No runners available
            return False

        # We have a notebook runner, and a job, get the job
        notebook, varsi, progress_callback, result_callback = self.jobs.pop(0)  # Remove from the beginning

        logging.info("Starting job....")
        # Result callback gets the varso dict
        runner.run_notebook(notebook, varsi, progress_callback=progress_callback, result_callback=result_callback)
        self.no_of_active_runners += 1
        self.active_runners.append(runner)

    def done(self):
        logging.info("...job complete.")
        for r in self.active_runners[:]:
            if r._is_active == False:
                self.active_runners.remove(r)
                self.runners.append(r)
                self.no_of_active_runners -= 1
                
    def create_runner(self):
        r = NotebookRunner()
        r._execute('%matplotlib inline')               
        r.notebook_completed.connect( self.done )
        self.runners.append( r )

    def topup_runners(self):
        if len(self.runners) < self.no_of_runners:
            self.create_runner()

    def create_runners(self):
        for n in range(self.no_of_runners):
            self.create_runner()

    def restart(self):
        for r in self.runners:
            r.restart_kernel('Restarting...', now=True)
        
        for r in self.active_runners:
            r.run_notebook_completed(True, "Aborted")
            r.restart_kernel('Restarting...', now=True)
            self.runners.append(r)
        self.active_runners = []
        
    def interrupt(self):
        for r in self.runners:
            r.interrupt_kernel()
        
        for r in self.active_runners:
            r.run_notebook_completed(True, "Aborted")
            r.interrupt_kernel()
            self.runners.append(r)
        self.active_runners = []
