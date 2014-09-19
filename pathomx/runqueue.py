import logging

from collections import namedtuple

from .qt import *

from IPython.qt.base_frontend_mixin import BaseFrontendMixin
from IPython.qt.inprocess import QtInProcessKernelManager as KernelManager
from IPython.qt.console.ansi_code_processor import QtAnsiCodeProcessor

from copy import deepcopy
from datetime import datetime
import re


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
        self.kernel_client.start_channels(stdin=False) #, hb=False)
        
        # Update progressBars: note that this will not function with current InProcess Kernel
        # requires separate thread + variable messaging implementation
        #self._progress_timer = QTimer()
        #self._progress_timer.timeout.connect(self.progress)
        #self._progress_timer.start(1000)
        

    def __del__(self):
        if self.kernel_client:
            self.kernel_client.stop_channels()
        if self.kernel_manager:
            self.kernel_manager.shutdown_kernel()
            
    def progress(self):
        progress = self.kernel_manager.kernel.shell.user_ns['_progressBar']
        if self._progress_callback:
            self._progress_callback(progress)

    def run_notebook(self, code, varsi, progress_callback=None, result_callback=None):
        '''
        Run all the cells of a notebook in order and update
        the outputs in-place.
        '''
        
        self.code = code
        self.varsi = varsi
        
        self._progress_callback = progress_callback
        self._result_callback = result_callback
        self._is_active = True

        self._result_queue = [] # Cache for unhandled messages
        self._cell_execute_ids = {}
        self._execute_start = datetime.now()
        
        self.kernel_manager.kernel.shell.push({'varsi':varsi})
        self._execute(r'''from pathomx.kernel_helpers import pathomx_notebook_start, pathomx_notebook_stop
pathomx_notebook_start(varsi, vars());''')

        # We split the code into 'cells' here so we get UI response between those chunks
        # this allows progress update/etc. to be displayed
        # TODO: Implement a method for a running process to mark it's progress specifically
        code_cells = re.split('\n(?=\w.*[^:]\n)', code) # Split only where not indented (blocks are processed together)
        cell_pc = 100.0 / len(code_cells)
        
        for n, cell in enumerate(code_cells):
            msg_id = self._execute(cell)
            logging.debug('Cell number %d; %s' % ( n, msg_id) )
            progress = n * cell_pc
            self._cell_execute_ids[ msg_id ] = (cell, n, progress) # Store cell and progress        

        logging.debug("Runing notebook; startup message: %s" % msg_id)

        self._final_msg_id = self._execute(r'''pathomx_notebook_stop(vars());''')
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
            result['varso'] = self.kernel_manager.kernel.shell.user_ns['varso']

        #result['notebook'] = None

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
        
        #self.progress.emit( pc )
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
            traceback = '\n'.join(content['traceback'])
            self.run_notebook_completed(error=True, traceback=traceback)
            
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
        #out = NotebookNode(output_type=msg_type)

        if 'execution_count' in content:
            #self._current_cell['prompt_number'] = content['execution_count']
            pass #out.prompt_number = content['execution_count']

        if msg_type in ('status', 'pyin', 'execute_input'):
            return

        elif msg_type == 'stream':
            pass
            #out.stream = content['name']
            #out.text = content['data']

        elif msg_type in ('display_data', 'pyout'):
            # Is this handled in _handle_execute_result?
            for mime, data in content['data'].items():
                try:
                    attr = self.MIME_MAP[mime]
                except KeyError:
                    raise NotImplementedError('unhandled mime type: %s' % mime)

                #setattr(out, attr, data)
            return

        elif msg_type == 'pyerr':
            # Is this handled in _handle_execute_errror?
            # out.ename = content['ename']
            # out.evalue = content['evalue']
            # out.traceback = content['traceback']
            return 

        elif msg_type == 'clear_output':
            self._current_cell['outputs'] = []
            return

        elif msg_type == 'execute_reply':
            pass

        else:
            raise NotImplementedError('unhandled iopub message: %s' % msg_type)

        #self._current_cell['outputs'].append(out)

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

            #out = NotebookNode(output_type='display_data')
            for mime, data in msg['content']['data'].items():
                try:
                    attr = self.MIME_MAP[mime]
                except KeyError:
                    raise NotImplementedError('unhandled mime type: %s' % mime)

                #setattr(out, attr, data)            
            
            #cell['outputs'].append(out)

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

    def __init__(self):
        super(NotebookRunnerQueue, self).__init__() 
        self.runner = None
        self.jobs = []  # Job queue a tuple of (notebook, success_callback, error_callback)
        self.start.connect(self.run)

    def start_timers(self):
        self._run_timer = QTimer()
        self._run_timer.timeout.connect(self.run)
        self._run_timer.start(1000)  # Auto-check for pending jobs every 1 second; this shouldn't be needed but some jobs get stuck(?)

    def add_job(self, nb, varsi, progress_callback=None, result_callback=None):
        # We take a copy of the notebook, so changes aren't applied back to the source
        # ensuring each run starts with blank slate
        self.jobs.append(( deepcopy(nb), varsi, progress_callback, result_callback))
        self.start.emit() # Auto-start on every add job

    def run(self):
        # Check for jobs
        if not self.jobs:
            return False
            
        logging.info('Currently %d jobs remaining' % len(self.jobs))

        if self.runner is None or self.runner._is_active == True:
            return False
            
        self.runner._is_active = True

        # We have a notebook runner, and a job, get the job
        notebook, varsi, progress_callback, result_callback = self.jobs.pop(0)  # Remove from the beginning

        logging.info("Starting job....")
        # Result callback gets the varso dict
        self.runner.run_notebook(notebook, varsi, progress_callback=progress_callback, result_callback=result_callback)

    def done(self):
        logging.info("...job complete.")
        self.runner._is_active = False
                
    def restart(self):
        self.runner.restart_kernel('Restarting...', now=True)
        self.runner._is_active = False
        
    def interrupt(self):
        self.runner.interrupt_kernel()
        self.runner._is_active = False
        
    def create_runner(self):
        self.runner = NotebookRunner()
        self.runner._execute('%matplotlib inline')               
        self.runner.notebook_completed.connect( self.done )
    
