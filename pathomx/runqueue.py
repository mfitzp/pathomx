import logging

from collections import namedtuple, defaultdict

from .qt import *

from IPython.qt.base_frontend_mixin import BaseFrontendMixin
from IPython.qt.inprocess import QtInProcessKernelManager as KernelManager
from IPython.qt.console.ansi_code_processor import QtAnsiCodeProcessor

from IPython.parallel import Client, TimeoutError, RemoteError
from IPython.utils.pickleutil import use_dill
use_dill()

from datetime import datetime
import re
import os
import sys
from subprocess import Popen
from IPython.parallel.apps import ipclusterapp

from matplotlib import rcParams

# Kernel is busy but not because of us
STATUS_BLOCKED = 'blocked'

# Normal statuses
STATUS_READY = 'ready'

STATUS_ACTIVE = 'active'
STATUS_COMPLETE = 'complete'

# Error status
STATUS_ERROR = 'error'

AR_PUSH = 1
AR_EXECUTE = 2
AR_PULL = 3

PROGRESS_REGEXP = re.compile("____pathomx_execute_progress_(.*)____")

# Job submitted as initiating tool
# Pre-calculate the execution order and flow (save the round-trip execution) stopping at paused tools
# - the set of this available on job object for mapping
# Compare to existing jobs in the queue; if any tool's lists are a subset of this tools list kill that job
# - is this interactive mode only? decided later; may require override
#
# Initiate job
# - check run flag (still to run)
# Set all included tools as status-clear
# Run first task, with callback trigger to next step (+callback to tool; multiples? how to handle)
# - Each run-task should check run-flag before continuing
#
# Job complete; delete job from queue

class Runner(QObject):
    """
    A runner object that handles running an Task object on an IPython cluster kernel

    Each Task object consists of multiple Exec objects which can be executed immediately in turn.
    (scheduling is already handled by the Job object the Task is provided by).

    Each Exec can include varsi (vars in), code, varso (vars out) and pre-execution non-Python code setup.
    The code is passed as a list of multiple objects, which must be executed then watched for output
    via the AsyncResult object.

    Callbacks are fired on the originating Exec object for progress, success, failure of any step.
    """

    def __init__(self, k, *args, **kwargs):
        super(Runner, self).__init__(*args, **kwargs)

        self.k = k

        # Reset settings
        self.reset()
        self._status = STATUS_READY

        # Check over ASync objects for updated status
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.check_status)
        self.status_timer.start(100)  # 0.1 sec

        # Trigger to update the progress of running Exec objects (scan stdout of ARs for progress)
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.check_progress)
        self.progress_timer.start(500)  # 1 sec

    @property
    def is_active(self):
        return self._is_active or self.k.queue_status()['queue'] > 0

    @property
    def status(self):
        if self._status == STATUS_READY and self.k.queue_status()['queue'] > 0:
            return STATUS_BLOCKED
        else:
            return self._status

    def setup_language(self, language):
        if language == 'r':
            # Init R library loader (will take time first time; but instant thereafter)
            self.k.execute(r'''%load_ext rpy2.ipython''')

        elif language == 'matlab':
            # Init MATLAB
            self.k.execute(r'''%load_ext pymatbridge''')

    def run(self, task):
        """
        Takes a single Task object and executes all Exec objects from within immediately on the available kernel.
        """

        if self.is_active:
            logging.error("Runner kernel not ready, but it got a job. Job ignored.")
            return False

        # Dicts for accessing the running Exec from the AR and vice versa
        self.reset()

        self._is_active = True
        self._status = STATUS_ACTIVE

        self.task = task

        for e in task.execute:

            # Clear workspace before each task run
            self.k.execute('%reset_selective -f [^_]')

            # Execute language-specific setup if required; note: fails silently!
            self.setup_language(e.language)
            ars = []

            if e.varsi:
                ar = self.k.push(e.varsi, block=False)
                ars.append(ar)
                self.ar_types[ar] = AR_PUSH

            if e.code:
                for c in e.code:
                    ar = self.k.execute(c, block=False)
                    ars.append(ar)
                    self.ar_types[ar] = AR_EXECUTE

            if e.varso:
                for v in e.varso:
                    ar = self.k.pull(v, block=False)
                    ars.append(ar)
                    self.ar_types[ar] = AR_PULL

            self.ar_by_exec[e] = ars

    def check_status(self):
        """
        Automatically check for progress on the executing Execute objects.

        We can iterate the dict of ASyncResult objects by original Execute. Using the
        type of the ASyncResult we can then perform the appropriate action on the data,
        using the Execute-linked callbacks to pass the data on. This makes handling
        different Execute types relatively seamless.

        """
        if not self.is_active:
            return False

        ars_waiting = False

        for ex, ars in self.ar_by_exec.items():
        # e is the original Exec object (for callbacks)
        # ars is a list of ASyncResult objects originating from it

        # Finally iterate each object
            for ar in ars:
                ar_type = self.ar_types[ar]
                try:
                    ar_result = ar.get(0)

                except TimeoutError:
                    ars_waiting = True

                except RemoteError as e:
                    # Handle all code exceptions and pass back the exception
                    result = {
                            'status': -1,
                            'traceback': '\n'.join(e.render_traceback()),
                            'stdout': self.stdout + ar.stdout,
                    }

                    # Emit the task-error signal (cancel dependencies)
                    self.task.error.emit()

                    # Emit the error via the Execute object (to the tool)
                    ex.result.emit(result)

                    self._status = STATUS_ERROR
                    # Interrupt and stop here
                    self.reset()

                else:
                    # Success on retrieve
                    if ar_type == AR_PUSH:
                        ex.complete.emit()

                    if ar_type == AR_EXECUTE:
                        # We should emit the complete notification here; but we have no way of
                        # knowing whether the AR relates the first, or 50th exec that was triggered?
                        self.stdout += ar.stdout
                        ex.complete.emit()

                    if ar_type == AR_PULL:
                        result = {
                                'status': 0,
                                'varso': ar_result,
                                'stdout': self.stdout + ar.stdout,
                                'kernel': id(self.k)
                        }
                        ex.complete.emit()
                        ex.result.emit(result)

        # Check if all jobs have completed; then shutdown and exit
        if not ars_waiting:
            if self.task:
                # Emit the task-complete signal (allow dependencies to run)
                self.task.complete.emit()

            # Reset this kernel, ready to go
            self._status = STATUS_READY
            self.reset()

    def reset(self):
        self._is_active = False  # Release this kernel
        self.ar_by_exec = {}
        self.ar_types = {}
        self.stdout = ""
        self.task = None

    def check_progress(self):
        if self.status != STATUS_ACTIVE:
            return False



        for ex, ars in self.ar_by_exec.items():
            for ar in ars:
                lines = ar.stdout.split('\n')
                for l in lines:
                    m = PROGRESS_REGEXP.match(l)
                    if m:
                        ex.progress.emit(float(m.group(1)))


class Execute(QObject):
    """
    Execute is a set of execution step to run on the kernel

    An exec consists of the code to run (a list) and supports callbacks
    for all the possible results of that execution: success, failure, result, etc.
    """

    result = pyqtSignal(dict)
    progress = pyqtSignal(float)
    complete = pyqtSignal()

    def __init__(self, varsi=None, code=None, varso=None, language="python", metadata=None):
        super(Execute, self).__init__()

        self.language = language

        self.varsi = varsi
        self.code = code
        self.varso = varso

        self.metadata = metadata


class Task(QObject):
    """
    Task is a set of Exec objects to run on the kernel

    An task consists of the Code objects to run (a list).

    The Runner takes the Task and executes all Exec objects *immediately* on the kernel,
    lined up in order. Execution then continues until completion, or error. In
    the event of error the kernel is interrupted and execution will stop.

    When the 'complete' function is called on this object, it is disposed
    of by the parent job.

    The parent job can connect to these events and pass the even onto the relevant handler.
    """

    status = pyqtSignal()
    error = pyqtSignal()

    traceback = pyqtSignal(dict)

    complete = pyqtSignal()

    def __repr__(self):
        s = "Task %s: " % id(self)
        if self.execute:
            for e in self.execute:
                s += "%s\n" % e.metadata
        return s

    def __init__(self, job, execute=None, dependencies=None):
        super(Task, self).__init__()

        self.job = job

        if dependencies is None:
            dependencies = []

        # Execs that must run before this task
        self.dependencies = dependencies

        # Execution
        self.execute = execute

        # Kernel that this Exec is/was running on
        self.kernel = None

        # Complete callback (default) others can be added
        self.complete.connect(self.completed)
        self.error.connect(self.errored)

    def ready(self):
        pass

    def completed(self):
        # Remove this exec object from the running list
        self.job.tasks_running.remove(self)
        # Add ourselves to the complete list
        self.job.tasks_complete.append(self)

    def errored(self):
        self.job.tasks_running.remove(self)
        self.job.tasks_errored.append(self)


class Job(QObject):
    """
    A Job to be executed on the available kernels.

    Each Job can be as simple or as complex as needed, but presents a consistent API to the Queue system
    and kernel. This base Job class handles the simplest case of executing bare script on the remote server.
    For a more complex implementation see ToolJob, which builds a series of Exec objects from a given tool.

    The Job.next() callback returns a Task consisting of [list] of Exec objects to pass onto the kernel Runner.
    Each Exec object must handle it's own callbacks, result handling etc. transparently.

    All objects passed in single [Exec] must be capable of running simultaneously on the target
    kernel, passed Exec objects will be executed in turn, with no dependency checking: i.e.
    the job object itself must handle the appropriate passing/preparation for dependent variables
    and pass these through.

    """

    def __init__(self, name='Untitled'):
        super(Job, self).__init__()

        self.name = name

        self.status = STATUS_READY
        self.tasks_queued = []
        self.tasks_running = []
        self.tasks_complete = []
        self.tasks_errored = []

        self.is_active = False

        # We compare by sets by default (to support tool-wise comparison in ToolJobs)
        # setting identity to a set of self id ensures will always fail the test for comparison with another job
        self.identity = set([id(self)])

    def __gt__(self, other):
        if isinstance(other, Job):
            if self.identity.issuperset(other.identity):
                return True
        else:
            return super(Job, self).__gt__(other)

    def __ge__(self, other):
        if isinstance(other, Job):
            if self.identity == other.identity or self.identity.issubset(other.identity):
                return True
        else:
            return super(Job, self).__gt__(other)

    def start(self):
        """
        Pre-run initialisation
        """
        self.is_active = True
        self.status = STATUS_ACTIVE

    def stop(self):
        """
        Post-run cleanup
        """
        self.is_active = False
        # Don't replace error status
        if self.status == STATUS_ACTIVE:
            self.status = STATUS_COMPLETE

    def next(self, kernel=None):
        """
        Return the next available Task object (kernel is ignored)
        """
        try:
            e = self.tasks_queued.pop()

        except IndexError:  # Empty exec list
            self.is_active = False
            return None

        else:
            self.tasks_running.append(e)
            return e

    @property
    def executes_queued(self):
        return [e for t in self.tasks_queued for e in t.execute]

    @property
    def executes_complete(self):
        return [e for t in self.tasks_complete for e in t.execute]

    @property
    def executes_errored(self):
        return [e for t in self.tasks_errored for e in t.execute]

    @property
    def executes_running(self):
        return [e for t in self.tasks_running for e in t.execute]

    @property
    def executes_all(self):
        return self.executes_queued + self.executes_complete + self.executes_errored + self.executes_running

    @property
    def is_complete(self):
        return len(self.tasks_queued + self.tasks_running) == 0


class CodeJob(Job):

    def __init__(self, code, language='python'):
        super(CodeJob, self).__init__()

        # Create a single code-object job and push it to the queue
        self.tasks_queued.append(
            Task(self, execute=[Execute(code, language=language)])
        )


class ToolJob(Job):
    """
    Job object to run a given tool, and all subsequent tools in the workflow

    Each job encapsulates the full set of tool runs that must occur to complete the execution.
    This involves traversing from the initiating tool through the tree of
    watchers, until hitting a dead end or a paused tool.

    The result is a list of tools that are to be executed in turn. Metadata (config, code)
    from the tools is locked, and a set of generic metadata (rcParams, styles) is locked
    for the entire job.

    Initiation of execution starts at T0.

    All tools are set to status 'unknown' on the initiation of execution.

    Callbacks are registered for various steps; the job object acts as the intermediary
    passing the execution onto the relevant tool.

    Next execution is triggered on .next() and will attempt to find a tool who's parents
    have all executed. The optional kernel parameter will attempt to execute on the
    best kernel, avoiding redundant variable passing. If unable, a set of varsi will be passed.

    On error, any children of the failed tool (and their children) are removed, other execution
    may continue as expected.

    A set list of tool ids is available for checking vs. other jobs. If a newer job is a superset
    of an existing job, the existing job is deleted.
    """

    def __init__(self, tool, varsi, *args, **kwargs):
        """
        Generate an execution queue from the supplied singular tool
        current tool is in the head position, execution will start from there.

        As passing each tool, lock the code and config into the tool ensure static
        for the whole of execution, ignore future changes.

        A set of tool objects will uniquely describe this job,
        and allow superset or == jobs to delete this job.
        """
        super(ToolJob, self).__init__(*args, **kwargs)
        # Global varsi must be passed at the start of each Exec job as may not be present otherwise
        # otherwise. Stored here for re-use. n.b. within a Job these should not change (persistance)
        # may need to account for this by taking a copy of styles here?
        # self.global_varsi = {
        #    'rcParams': {k: v for k, v in rcParams.items() if k not in strip_rcParams},
        #    '_pathomx_database_path': os.path.join(utils.scriptdir, 'database'),
        #    'styles': styles,
        #    }

        global_varsi = varsi.copy()

        # Build the queue of Exec objects;
        self.execs_queue = []
        self.exec_tool_lookup = {}
        tool_task_lookup = {}

        process_queue = [tool]
        process_done = []

        tool_list = []
        exec_list = []

        previous_tool = None

        while len(process_queue) > 0:

            # Remove duplicates
            process_queue = list(set(process_queue))
            t = process_queue.pop(0)  # From front

            # Check for what that this tool depends on
            parents = t.get_parents()

            if len(parents) > 0 \
                and len(set(parents) & set(process_queue)) > 0:
                # waiting on something here, push to the back of the list for later
                process_queue.append(t)
                continue

            # Build an exec object for the given tool: note that at this point we cannot determine whether the
            # vars are on the correct kernel. We can't seed at this point either, as the result of subsequent
            # calculations will not be reflected. The solution is to populate Exec.varsi{} at runtime dispatch.
            # In order to make the neccessary data available at that time, we here store it via lookup.
            varsi = {
                    'config': t.config.as_dict(),
                    '_pathomx_tool_path': t.plugin.path,
                    '_pathomx_expected_output_vars': list(t.data.o.keys()),
                    }

            # Build the IO magic
            # - if the source did not run on the current runner we'll need to push the data over (later)
            io = {'input': {}, 'output': {}, }
            for i, sm in t.data.i.items():
                if sm:
                    mo, mi = sm
                    io['input'][i] = "_%s_%s" % (mi, id(mo.v))
                else:
                    io['input'][i] = None
            for o in t.data.o.keys():
                io['output'][o] = "_%s_%s" % (o, id(t))
            varsi['_io'] = io

            e = Execute(
                varsi=varsi,
                code=[
                      "from pathomx.kernel_helpers import pathomx_notebook_start, pathomx_notebook_stop, progress, open_with_progress; pathomx_notebook_start(vars());",
                      t.code,
                      "pathomx_notebook_stop(vars());",
                    ],
                varso=['varso'],
                language=t.language,
                metadata={'name': t.name, 'tool': t},
            )

            e.progress.connect(t.progress.emit)
            e.result.connect(t._worker_result_callback)

            # Store the tool for this Exec object; for dispatch calculation
            self.exec_tool_lookup[e] = tool

            watchers = [w.v for k, v in t.data.watchers.items() for w in v]
            for w in watchers:
                if w not in process_done and w not in process_queue:
                    # Put all watchers at the front of the list, this will iteratively ensure we can straight-line
                    # down at least one path once started
                    process_queue.insert(0, w)

            # Determine the position of the object
            # Is before fork; if there is more than 1 tool watching this one
            is_before_fork = len(watchers) > 1
            # Is the end of a fork (watchers have > 1 parent)
            is_end_of_fork = len([p for w in watchers for p in w.get_parents()]) > 1


            if previous_tool is not None and previous_tool not in parents:
                # We are not a direct descendant we're going to have to start a new Task.
                # There should be more effort to mitigate this in ordering of the task-queue
                task = Task(self, execute=exec_list)
                self.tasks_queued.append(task)

                for pt in tool_list:
                    tool_task_lookup[pt] = task

                exec_list = []
                tool_list = []

            # If this is the first execute object in the queue (list is empty), update it with the global vars for run
            # and store the head of branch tool for later dependencies
            if not exec_list:
                e.varsi.update(global_varsi)

            tool_list.append(t)
            exec_list.append(e)

            if is_before_fork or is_end_of_fork:
                # We've got >1 children, we need to create a split task again
                task = Task(self, execute=exec_list)
                self.tasks_queued.append(task)

                for pt in tool_list:
                    tool_task_lookup[pt] = task

                exec_list = []
                tool_list = []

            process_done.append(t)
            previous_tool = t

        if exec_list:  # Remainders
            task = Task(self, execute=exec_list)
            self.tasks_queued.append(task)

        logging.debug("task_queue: %s" % self.tasks_queued)


        # Apply the dependencies to each task: we need to do this at the end to avoid missing due to order
        for t in self.tasks_queued:
            if t.execute:
                e0 = t.execute[0]
                dependencies = []
                for ti in e0.metadata['tool'].get_parents():
                    if ti in tool_task_lookup:
                        dependencies.append(tool_task_lookup[ti])
                t.dependencies = dependencies

        self.tool_list = process_done

        # Store an identity for this job; we can use subset set matching to compare subsequent jobs
        self.identity = set([id(t) for t in self.tool_list])

    def start(self):
        if not self.is_active:
            # Reset all tools in this Job to clear-status (not ready)
            for t in self.tool_list:
                t.status.emit('ready')

        super(ToolJob, self).start()

    def next(self, kernel=None):
        """
        Request the next Task object to run on the specified kernel

        The provided kernel identifier is used to determine whether the
        parent tools' data must be sent through before execution. For
        linear execution the data passing can be handled complete
        kernel-side by variable copying, however on branched execution
        tool execution may occur on a kernel where the parent was not
        yet, or last, run. In this case the data must be passed over before
        in the variable in.

        The passing should be logged, and (post-send?) the tool updated to
        reflect that it's data is now *also* on the other kernel.

        ? callback on the vars push ?

        """
        if not self.tasks_queued:
            return None

        for t in self.tasks_queued[:]:
            if not t.dependencies or len(set(t.dependencies) - set(self.tasks_complete)) == 0:
                # We have an Exec not waiting on dependencies
                # Remove this task from the queue then continue on
                self.tasks_queued.remove(t)
                break

            if set(t.dependencies) & set(self.tasks_errored):
                # A dependency has errored, we can't run this task (ever); add to error list and skip it
                self.tasks_queued.remove(t)
                self.tasks_errored.append(t)

        else:
            return False  # Waiting

        # Handle the exec here
        # We receive the kernel identifier from the Queue, so here we can determine whether the parent(s)
        # tools were run on the same kernel. There are two scenarios here:
        #   - 1. Initiating a Job, single/multiple parent tool, needs feeding in to startup
        #   - 2. Fork parallel job, needs feeding in to continue
        #
        # Note, we need to ensure we are sending up-to-date data (i.e. the previous Exec has finished, and results
        # have been exported before we start on with the next). This locking can be achieved using the Exec dependencies.

        # Check whether the parents of the head-of-queue were run on this kernel
        # Get the original tool; build a list of all parents + their respective kernels

        # Iterate each, find if it's current data is on *this* kernel, if so carry on
        # if not, we'll need to pass it in (can stuff it into the first Exec, or add a new one?)
        varsi = {}
        tools_to_move = []
        # Apply the dependencies to each task: we need to do this at the end to avoid missing due to order
        if t.execute:
            # We only need to get dependencies for the head Execution; as the branching logic means that >1 parent
            # anywhere >1 parent == a new Task
            e0 = t.execute[0]
            tool = e0.metadata['tool']
            # Build the dict to send,
            # will also want to build some kind of callback to track this
            for i, sm in tool.data.i.items():
                if sm:
                    mo, mi = sm

                    if id(kernel) not in mo.v.current_data_on_kernels:
                        # We need to push the actual data; this should do it?
                        varsi['_%s_%s' % (mi, id(mo.v))] = tool.data.get(i)
                        tools_to_move.append(mo.v)

        # We've got something to move between kernels
        if varsi:
            e = Execute(varsi=varsi)
            # FIXME: This will need a callback wrapped function to pass the extra data without some nasty shit
            e.complete.connect(lambda: self.complete_move_data_to_kernel(kernel, tools_to_move))
            # Put this Execute instruction at the head of list
            t.execute.insert(0, e)

        self.tasks_running.append(t)
        return t

    @staticmethod
    def complete_move_data_to_kernel(kernel, tools):
        for t in tools:
            t.current_data_on_kernels.add(id(kernel))


class Queue(QObject):
    """
    RunManager manages jobs in an internal Queue, automating running,
    handling and cleanup. Scheduling to specific cluster kernels
    for the current job is also handled, depending on the cluster
    for the run-status of the previous job.


    """

    start = pyqtSignal()
    updated = pyqtSignal()

    def __init__(self):
        super(Queue, self).__init__()

        self.runners = []
        self.jobs = []  # Job queue a tuple of (notebook, success_callback, error_callback)
        self.jobs_completed = []

        self.start.connect(self.run)

        self.p = None
        self.client = None

    def start_timers(self):
        self._run_timer = QTimer()
        self._run_timer.timeout.connect(self.run)
        self._run_timer.start(100)  # Auto-check for pending jobs every 0.1 second; this shouldn't be needed but some jobs get stuck(?)

        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self.cleanup)
        self._cleanup_timer.start(15000)  # Re-check runners every 15 second

        self._cluster_timer = QTimer()
        self._cluster_timer.timeout.connect(self.create_runners)
        self._cluster_timer.start(5000)  # Re-check runners every 5 seconds

    def add(self, job):
        """
        Add a job to the queue.

        Add a created job to the queue. A test is first performed to remove all equivalent (or lesser) jobs from
        the queue, to improve responsiveness of UI twiddling.
        :param job:
        :return:
        """
        for j in self.jobs[:]:
            if (not j.is_active) and job >= j:
                self.jobs.remove(j)

        self.jobs.append(job)

        # We fire an additional
        self.start.emit()

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

        job = self.jobs[0]  # Get the job at the front of the queue
        # (? can we be more intelligent about this is there are a lot of runners available)

        # Identify the best runner for the job
        # - which runners are available
        # - which runners were the source data generated on
        # - which source(s) have the largest data size
        for runner in self.runners:
            if not runner.is_active:
                # That'll do for now
                break
        else:
            # Can't run now, we'll have to wait
            return False

        # Initialise the job (this is a no-op if already running)
        job.start()

        # Get the details for the next execution step
        e = job.next(kernel=runner.k)

        if e is False:
            # Job is waiting on something to complete; wait and trigger a post-poned fire of self.run()
            return False

        elif e is None:
            # Job has completed; let it go
            self.jobs.remove(job)
            job.stop()
            self.jobs_completed.append(job)

        else:
            # If we're here, we've got an Exec object in e, that is good to go on the current runner
            runner.run(e)

    def cleanup(self):
        for j in self.jobs_completed[:]:
            if j.is_complete:
                self.jobs_completed.remove(j)

    def restart(self):
        self.stop_cluster()
        self.create_runners()

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

        if self.client:
            self.client.shutdown()
            self.client = None

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
            # self.runners = [self.in_process_runner]
            self.start_cluster()

        elif self.p.poll() is None:
            # Create matching runners for the client
            # note that these may already exist; we need to check
            if self.client is None:
                self.client = Client(timeout=5)

            for k in self.client:
                found = False
                for r in self.runners:
                    if k.targets == r.k.targets:
                        found = True

                if not found:
                    runner = Runner(k)
                    runner.k.execute('%reset -f')
                    runner.k.execute('%matplotlib inline')
                    runner.k.apply(use_dill)
                    self.runners.append(runner)



        else:
            # We've got a -value for poll; it's terminated this will trigger restart on next poll
            self.stop_cluster()


class ExecuteOnly(object):
    language = 'python'

    def __init__(self, code):
        self.code = code
