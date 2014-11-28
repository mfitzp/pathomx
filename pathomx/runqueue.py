import logging

from collections import namedtuple

from .qt import *

from IPython.qt.base_frontend_mixin import BaseFrontendMixin
from IPython.qt.inprocess import QtInProcessKernelManager as KernelManager
from IPython.qt.console.ansi_code_processor import QtAnsiCodeProcessor

from IPython.parallel import Client, TimeoutError, RemoteError

from datetime import datetime
import re
import os
import sys
from subprocess import Popen
from IPython.parallel.apps import ipclusterapp

# Kernel is busy but not because of us
STATUS_BLOCKED = -1

# Normal statuses
STATUS_READY = 0
STATUS_RUNNING = 1
STATUS_COMPLETE = 2
STATUS_ERROR = 3


# from pkg_resources import load_entry_point
# load_entry_point('ipython==3.0.0-dev', 'console_scripts', 'ipcluster')()
# IPython.parallel.apps.ipclusterapp:launch_new_instance'


# FIXME; we need to base-class the runner code
def setup_languages(execute, language):
    if language == 'r':
        # Init R library loader (will take time first time; but instant thereafter)
        execute(r'''%load_ext rpy2.ipython''')

    elif language == 'matlab':
        # Init MATLAB
        execute(r'''%load_ext pymatbridge''')


class ClusterRunner(QObject):
    """
    A runner object that handles running IPython code on an IPython cluster for 
    parallel processing without blocking the UI.
    """
    pass

    def __init__(self, e, *args, **kwargs):
        super(ClusterRunner, self).__init__(*args, **kwargs)

        self.e = e
        self.ar = None
        self.aro = None
        self._is_active = False
        self._status = STATUS_READY
        self.stdout = ""
        '''
        Runner metadata;
            - tool-metadata (?):
                - last-run kernel [check for lookup/push requirement before starting]
                - 
        '''

        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.check_status)
        self.status_timer.start(100)  # 0.1 sec

        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.check_progress)
        self.progress_timer.start(1000)  # 1 sec

    @property
    def is_active(self):
        return self._is_active or self.e.queue_status()['queue'] > 0

    @property
    def status(self):
        if self._status == STATUS_READY and self.e.queue_status()['queue'] > 0:
            return STATUS_BLOCKED
        else:
            return self._status

    def run(self, tool, varsi, progress_callback=None, result_callback=None):
        code = tool.code

        self._is_active = True
        self._status = STATUS_RUNNING
        self.stdout = ""

        self._progress_callback = progress_callback
        self._result_callback = result_callback

        # Check metadata to see if this kernel has the outputs for the previous tool
        self.e.execute('%reset_selective -f [^_]')
        self.e.push({'varsi': varsi})
        self.e.execute(r'''from pathomx.kernel_helpers import pathomx_notebook_start, pathomx_notebook_stop, progress, open_with_progress
pathomx_notebook_start(varsi, vars());''')

        setup_languages(self.e.execute, tool.language)

        self.ar = self.e.execute(code)
        self.e.execute(r'''pathomx_notebook_stop(vars());''')  # This will queue directly above the main code block

    def check_status(self):
        result = {}

        if self.ar:

            self.stdout = self.ar.stdout
            try:
                r = self.ar.get(0)
            except TimeoutError:
                pass
            except RemoteError as e:
                # Handle all code exceptions and pass back the exception
                result['status'] = -1
                result['traceback'] = '\n'.join(e.render_traceback())
                result['stdout'] = self.stdout
                self._result_callback(result)
                self.ar = None
                self._is_active = False  # Release this kernel
                self._status = STATUS_ERROR

            else:
                self.ar = None
                self.aro = self.e.pull('varso', block=False)
                self._status = STATUS_COMPLETE

        elif self.aro:
            try:
                varso = self.aro.get(0)
            except TimeoutError:
                pass
            except RemoteError as e:
                result['status'] = -1
                result['traceback'] = '\n'.join(e.render_traceback())
                result['stdout'] = self.stdout
                result['varso'] = []
                self._result_callback(result)
                self.aro = None
                self._is_active = False  # Release this kernel
                self._status = STATUS_ERROR

            else:
                self.aro = None
                result['status'] = 0
                result['varso'] = varso
                result['stdout'] = self.stdout
                self._result_callback(result)
                self._is_active = False  # Release this kernel
                self._status = STATUS_READY

    def check_progress(self):
        if self.ar and self._progress_callback:
            lines = self.ar.stdout.split('\n')
            cre = re.compile("____pathomx_execute_progress_(.*)____")
            for l in lines:
                m = cre.match(l)
                if m:
                    self._progress_callback(float(m.group(1)))
            else:
                return None


class InProcessRunner(BaseFrontendMixin, QObject):
    '''
    A runner object that handles running the running tool code via an in-process IPython
    kernel. Base off initial runipy code amended to handle in-process running and the IPython FrontendWidget.
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
        super(InProcessRunner, self).__init__(*args, **kwargs)
        # FrontendWidget protected variables.
        self._kernel_manager = None
        self._kernel_client = None
        self._request_info = {
            'execute': {}
        }

        self._callback_dict = {}

        self._result_queue = []
        self._final_msg_id = None
        self._cell_execute_ids = {}

        self.is_active = False
        self.status = STATUS_READY

        self._executing = False

        # Set flag for whether we are connected via localhost.
        self._local_kernel = kwargs.get('local_kernel',
                                    InProcessRunner._local_kernel)

        self.kernel_manager = KernelManager()
        self.kernel_manager.start_kernel()

        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()

    def __del__(self):
        if self.kernel_client:
            self.kernel_client.stop_channels()
        if self.kernel_manager:
            self.kernel_manager.shutdown_kernel()

    def run(self, tool, varsi, progress_callback=None, result_callback=None):
        '''
        Run all the cells of a notebook in order and update
        the outputs in-place.
        '''
        self.is_active = True
        self.varsi = varsi

        self._progress_callback = progress_callback
        self._result_callback = result_callback

        self._result_queue = []  # Cache for unhandled messages
        self._cell_execute_ids = {}
        self._execute_start = datetime.now()

        self._execute('%reset_selective -f [^_]')
        self.kernel_manager.kernel.shell.push({'varsi': varsi})
        self._execute(r'''from pathomx.kernel_helpers import pathomx_notebook_start, pathomx_notebook_stop, progress, open_with_progress
pathomx_notebook_start(varsi, vars());''')

        setup_languages(self._execute, tool.language)

        msg_id = self._execute(tool.code)
        self._cell_execute_ids[msg_id] = (tool.code, 1, 100)  # Store cell and progress
        self._final_msg_id = self._execute(r'''pathomx_notebook_stop(vars());''')

    def run_completed(self, error=False, traceback=None):
        logging.info("Notebook run took %s" % (datetime.now() - self._execute_start))
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

        self.is_active = False
        if self._result_callback:
            self._result_callback(result)

    def _execute(self, source):
        """ Execute 'source'. If 'hidden', do not show any output.

        See parent class :meth:`execute` docstring for full details.
        """

        msg_id = self.kernel_client.execute(source, True)
        self._request_info['execute'][msg_id] = self._ExecutionRequest(msg_id, 'user')
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
            return self.run_completed()

        if msg_id not in self._cell_execute_ids:
            return

        (self._current_cell, n, pc) = self._cell_execute_ids[msg_id]

        logging.info("Execute cell %d complete in %s" % (n, datetime.now() - self._execute_start))

        #self.progress.emit( pc )
        if self._progress_callback:
            self._progress_callback(pc)

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
        if content['ename'] == 'SystemExit':
            keepkernel = content['evalue'] == '-k' or content['evalue'] == 'True'
            self._keep_kernel_on_exit = keepkernel
            self.exit_requested.emit(self)
        else:
            traceback = '\n'.join(content['traceback'])
            self.run_completed(error=True, traceback=traceback)

    def _process_execute_ok(self, msg):
        """ Process a reply for a successful execution request.
        """
        pass

    def _handle_kernel_died(self, since_last_heartbeat):
        """Handle the kernel's death (if we do not own the kernel).
        """
        logging.warn("kernel died")
        self.reset()

    def _handle_kernel_info_reply(self, *args, **kwargs):
        pass

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

            if msg_id not in self._cell_execute_ids:  # Only on the in-process kernel can this happen
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


class RunManager(QObject):
    '''
    Auto-creating and managing distribution of notebook runners for notebooks.
    Re-population handled on timer. Keeping a maximum N available at all times.
    '''

    start = pyqtSignal()
    is_parallel = False

    # Store metadata about tools' last run for variable passing etc.
    run_metadata = {}

    def __init__(self):
        super(RunManager, self).__init__()

        self.runners = []
        self.jobs = []  # Job queue a tuple of (notebook, success_callback, error_callback)

        self.start.connect(self.run)

        self.p = None
        self.client = None

    def __del__(self):
        self.terminate_cluster()

    def start_timers(self):
        self._run_timer = QTimer()
        self._run_timer.timeout.connect(self.run)
        self._run_timer.start(1000)  # Auto-check for pending jobs every 1 second; this shouldn't be needed but some jobs get stuck(?)

        self._cluster_timer = QTimer()
        self._cluster_timer.timeout.connect(self.create_runners)
        self._cluster_timer.start(5000)  # Re-check runners every 5 seconds

    def add_job(self, tool, varsi, progress_callback=None, result_callback=None):
        # We take a copy of the notebook, so changes aren't applied back to the source
        # ensuring each run starts with blank slate
        self.jobs.append((tool, varsi, progress_callback, result_callback))
        self.start.emit()  # Auto-start on every add job

    @property
    def no_of_kernels(self):
        return len(self.runners)

    @property
    def no_of_active_kernels(self):
        return sum([1 if k.is_active else 0 for k in self.runners])

    def run(self):
        # Check for jobs
        if not self.jobs:
            return False

        logging.info('Currently %d jobs remaining' % len(self.jobs))

        # We have job, get it
        tool, varsi, progress_callback, result_callback = self.jobs.pop(0)  # Remove from the beginning

        # Identify the best runner for the job
        # - which runners are available
        # - which runners were the source data generated on
        # - which source(s) have the largest data size
        for runner in self.runners:
            if not runner.is_active:
                # That'll do for now
                break
        else:
            self.jobs.insert(0, (tool, varsi, progress_callback, result_callback))
            return False

        varsi['_pathomx_expected_output_vars'] = tool.data.o.keys()

        # Build the IO magic
        # - if the source did not run on the current runner we'll need to push the data over
        io = {'input': {}, 'output': {}, }
        for i, sm in tool.data.i.items():
            if sm:
                mo, mi = sm
                io['input'][i] = "_%s_%s" % (mi, id(mo.v))

                # Check if the last run of this occurred on the selected runner
                if id(mo.v) in self.run_metadata and \
                    self.run_metadata[id(mo.v)]['last_runner'] != id(runner):

                    # We need to push the actual data; this should do it?
                    varsi['_%s_%s' % (mi, id(mo.v))] = tool.data.get(i)
            else:
                io['input'][i] = None

        for o in tool.data.o.keys():
            io['output'][o] = "_%s_%s" % (o, id(tool))

        varsi['_io'] = io

        self.run_metadata[id(tool)] = {
            'last_runner': id(runner)
        }

        tool.logger.info("Starting job....")

        # Result callback gets the varso dict
        runner.run(tool, varsi, progress_callback=progress_callback, result_callback=result_callback)

    def restart(self):
        self.stop_cluster()

    def interrupt(self):
        self.runner.interrupt_kernel()
        
    def start_cluster(self):
        # Start IPython ipcluster with 4 engines
        self.p = Popen([sys.executable, ipclusterapp.__file__, 'start', '--n=4'], stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'))

    def stop_cluster(self):
        # Stop the ipcluster
        p = Popen([sys.executable, ipclusterapp.__file__, 'stop'], stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'))
        while p.poll() is None:  # Wait for the above to exit
            pass

        self.p = None
        self.client.shutdown()
        self.client = None
        self.runners = [self.in_process_runner]

    def terminate_cluster(self):
        if self.p:
            self.p.terminate()
            self.p = None

    def create_runners(self):
        # Check the status of runners and the cluster process
        # If cluster process dead (non-None return to p.poll)
        # kill and re-start (add config for this?) and then
        # create an in-process kernel and pop it on the queue
        # to keep things ticking

        if self.p is None:
            # Use the in-process runner for now
            self.runners = [self.in_process_runner]
            self.start_cluster()

        elif self.p.poll() is None:
            # Create matching runners for the client
            # note that these may already exist; we need to check
            if self.client is None:
                self.client = Client(timeout=5)

                # FIXME: Inline plots are fine as long as we don't do it on the cluster+the interactive kernel; this results
                # in an image cache being generated that breaks the pickle

            for e in self.client:
                found = False
                for r in self.runners:
                    if r is not self.in_process_runner and e.targets == r.e.targets:
                        found = True

                if not found:
                    runner = ClusterRunner(e)
                    runner.e.execute('%reset -f')
                    runner.e.execute('%matplotlib inline')
                    self.runners.append(runner)

            if len(self.runners) > 1:
                # We've got a running cluster
                # remove the in-process kernel from the queue
                if self.in_process_runner in self.runners:
                    self.runners.remove(self.in_process_runner)

        else:
            # We've got a -value for poll; it's terminated this will trigger restart on next poll
            self.stop_cluster()

    def create_user_kernel(self):
        # Create an in-process user kernel to provide dynamic access to variables
        # Start an in-process runner for the time being
        self.in_process_runner = InProcessRunner()
        self.in_process_runner.kernel_client.execute('%reset -f')
        #self.in_process_runner.kernel_client.execute('%matplotlib inline')
