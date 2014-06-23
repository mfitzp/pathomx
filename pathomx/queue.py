import logging
import sys
import traceback

from copy import deepcopy

from IPython.nbformat.current import reads, NotebookNode
from IPython.nbconvert.exporters import export as IPyexport
from IPython.nbconvert.exporters.export import exporter_map as IPyexporter_map

from IPython.utils.ipstruct import Struct
from .notebook_runner import NotebookRunner

from .qt import *
from . import threads

try:
    import cPickle as pickle
except:
    import pickle as pickle

ENABLE_THREADING = False
if ENABLE_THREADING:
    MAX_RUNNER_QUEUE = threads.threadpool.maxThreadCount()
else:
    MAX_RUNNER_QUEUE = 2  # Keep a spare


class NotebookRunnerQueue(object):
    '''
    Auto-creating and managing distribution of notebook runners for notebooks.
    Re-population handled on timer. Keeping a maximum N available at all times.
    '''

    def __init__(self, no_of_runners=MAX_RUNNER_QUEUE):

    # If we fall beneath the minimum top it up
        self.no_of_runners = no_of_runners
        self.runners = []
        self.no_of_active_runners = 0

        self.jobs = []  # Job queue a tuple of (notebook, success_callback, error_callback)

        if ENABLE_THREADING:
            self._create_runners_timer = QTimer()
            self._create_runners_timer.timeout.connect(self.topup_runners)
            self._create_runners_timer.start(1000)  # Repopulate queue every 1 second

        self.create_runners()

        self._run_timer = QTimer()
        self._run_timer.timeout.connect(self.run)
        self._run_timer.start(250)  # Auto-start every 1/4 second

    def add_job(self, nb, varsi, progress_callback=None, result_callback=None):
        self.jobs.append((nb, varsi, progress_callback, result_callback))

    def run(self):
        # Check for jobs
        if not self.jobs:
            return False

        try:
            r = self.runners.pop(0)  # Remove from the beginning
        except IndexError:
            # No runners available
            return False

        # We have a notebook runner, and a job, get the job
        notebook_source, varsi, progress_callback, result_callback = self.jobs.pop(0)  # Remove from the beginning

        # FIXME: Or not?
        # Note the runner will be discarded after the thread is up; a new one will be recreated
        # Not doing this leads to a Python thread pegged at 100% CPU for unknown reasons
        # Recreating is actually pretty quick anyway
        # Would be nicer to do that in another thread, but it also causes crashes. Oh well.
        def make_callback(r):
            return lambda: self.dec_active_runners()

        self.inc_active_runners()
        if ENABLE_THREADING:
            # Run in a thread
            threads.run(self.run_notebook, runner=r, varsi=varsi, notebook=notebook_source, progress_callback=progress_callback, success_callback=result_callback, finished_callback=make_callback(r))
        else:
            result_callback(self.run_notebook(runner=r, varsi=varsi, notebook=notebook_source, progress_callback=progress_callback))
            self.dec_active_runners()
            self.runners.append(r)  # If not multi-threading re-use the runners

    def inc_active_runners(self):
        self.no_of_active_runners += 1

    def dec_active_runners(self):
        self.no_of_active_runners -= 1

    @staticmethod
    def run_notebook(runner, notebook, varsi, progress_callback=None):
        runner.nb = notebook
        result = {}

        # Pickle all variables and import to the notebook (depickler)
        with open(varsi['_pathomx_pickle_in'], 'wb') as f:
            pickle.dump(varsi, f, -1)  # Highest protocol for speed

        def callback_fn(cb, n, m):
            QApplication.processEvents()
            cb(float(n) / m)

        def make_callback(cb, m):
            return lambda n: callback_fn(cb, n, m)

        try:
            runner.run_notebook(execute_cell_no_callback=make_callback(progress_callback, runner.count_code_cells()))
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            result['traceback'] = value
            result['status'] = -1
            varso = {}
        else:
            result['status'] = 0
            # Return input; temp
            with open(varsi['_pathomx_pickle_out'], 'rb') as f:
                varso = pickle.load(f)

        result['notebook'], resources = IPyexport(IPyexporter_map['html'], runner.nb)
        return (result, varso)

    def create_runner(self):
        self.runners.append(NotebookRunner(None, pylab=True, mpl_inline=True))

    def topup_runners(self):
        if len(self.runners) < self.no_of_runners:
            self.create_runner()

    def create_runners(self):
        for n in range(self.no_of_runners):
            self.create_runner()

    def restart(self):
        self.runners = []
        self.no_of_active_runners = 0
        self.create_runners()
