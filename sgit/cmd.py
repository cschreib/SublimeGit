# coding: utf-8
import os
import sys
import subprocess
import logging
import threading
import webbrowser
import queue
from datetime import datetime
from functools import partial
import sys
import traceback

def get_thread_stack(thread):
    frame = sys._current_frames().get(thread.ident, None)
    if not frame:
        return []

    return traceback.format_stack(f=frame)

import sublime

from .util import get_executable, get_setting, text_type
from .helpers import GitRepoHelper


logger = logging.getLogger('SublimeGit.cmd')
worker_logger = logging.getLogger('SublimeGitWorker')

class SublimeGitException(Exception):
    pass

worker_queue = queue.Queue(1)
output_queue = {}
output_queue_lock = threading.Lock()
last_task_id = 0
max_tries = 100

def get_output_queue(task_id):
    global output_queue_lock
    global output_queue

    with output_queue_lock:
        if not task_id in output_queue:
            output_queue[task_id] = queue.Queue(1)

        return output_queue[task_id]

def release_output_queue(task_id):
    global output_queue_lock
    global output_queue

    with output_queue_lock:
        if task_id in output_queue:
            del output_queue[task_id]

def process_queue_one():
    task_id, job = worker_queue.get(timeout=1)
    worker_logger.info("[%s,%s] got input, processing...", threading.get_ident(), task_id)

    try:
        outputs = job()
        worker_logger.info("[%s,%s] got output, sending...", threading.get_ident(), task_id)
    except Exception as e:
        worker_logger.warning("[%s,%s] got error: %s", threading.get_ident(), task_id, e)
        worker_logger.warning("[%s,%s] sending...", threading.get_ident(), task_id)
        outputs = SublimeGitException("Unhandled exception in queue command: %s" % e)

    get_output_queue(task_id).put(outputs, timeout=1)

    worker_logger.info("[%s,%s] sent", threading.get_ident(), task_id)

def process_queue():
    while True:
        try:
            worker_logger.debug("wait for input...")
            process_queue_one()
        except:
            worker_logger.debug("no input")
            pass

def next_task_id():
    global last_task_id
    last_task_id += 1
    task_id = last_task_id
    return task_id

def dump_worker_thread_stack(operation, task_id):
    worker_logger.warning("[%s,%s] %s timed out, worker thread stack:", threading.get_ident(), task_id, operation)
    for entry in get_thread_stack(worker_thread):
        worker_logger.warning(entry.replace('\r', '').split('\n')[0])

def push_new_job(task_id, job):
    num_tries = 0
    while True:
        try:
            worker_queue.put((task_id, job), timeout=0.1)
            return
        except Exception as e:
            worker_logger.info("[%s,%s] put timed out, waiting some more...", threading.get_ident(), task_id)
            num_tries += 1
            if num_tries == max_tries:
                dump_worker_thread_stack('put', task_id)
                raise e

def get_job_output(task_id):
    try:
        num_tries = 0
        queue = get_output_queue(task_id)

        while True:
            try:
                return queue.get(timeout=0.1)
            except Exception as e:
                worker_logger.info("[%s,%s] get timed out, waiting some more...", threading.get_ident(), task_id)
                num_tries += 1
                if num_tries == max_tries:
                    dump_worker_thread_stack('get', task_id)
                    raise e

    finally:
        release_output_queue(task_id)

worker_thread = threading.Thread(target=process_queue)
worker_thread.start()

class Cmd(object):
    started_at = datetime.today()
    last_popup_at = None

    executable = None
    bin = []
    opts = []

    # cmd helpers
    def _string(self, cmd, strip=True, *args, **kwargs):
        _, stdout, _ = self.cmd(cmd, *args, **kwargs)
        return stdout.strip() if strip else stdout

    def _lines(self, cmd, *args, **kwargs):
        _, stdout, _ = self.cmd(cmd, *args, **kwargs)
        stdout = stdout.rstrip()
        if not stdout:
            return []
        return stdout.split('\n')

    def _exit_code(self, cmd, *args, **kwargs):
        exit, _, _ = self.cmd(cmd, *args, **kwargs)
        return exit

    def build_command(self, cmd):
        bin = get_executable(self.executable, self.bin)
        return bin + self.opts + [c for c in cmd if c]

    def env(self):
        env = os.environ.copy()
        path = get_setting('git_force_path', [])
        if path:
            if isinstance(path, list):
                env['PATH'] = os.pathsep.join(path)
            elif isinstance(path, text_type):
                env['PATH'] = path
        return env

    def startupinfo(self):
        startupinfo = None
        if hasattr(subprocess, 'STARTUPINFO'):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        return startupinfo

    def decode(self, stream, encoding, fallback=None):
        if not hasattr(stream, 'decode'):
            return stream

        try:
            return stream.decode(encoding)
        except UnicodeDecodeError:
            if fallback:
                for enc in fallback:
                    try:
                        return stream.decode(enc)
                    except UnicodeDecodeError:
                        pass
            raise

    def worker_run(self, job, task_id=None):
        if not task_id:
            task_id = next_task_id()

        worker_logger.info("[%s,%s] running task", threading.get_ident(), task_id)

        if threading.get_ident() == worker_thread.ident:
            # We are already in the worker thread, execute immediately
            worker_logger.info("[%s,%s] immediate call", threading.get_ident(), task_id)
            outputs = job()
        else:
            # Schedule on the worker thread and wait for the output now
            try:
                worker_logger.info("[%s,%s] new input, sending...", threading.get_ident(), task_id)
                push_new_job(task_id, job)
                worker_logger.info("[%s,%s] wait for output...", threading.get_ident(), task_id)
                outputs = get_job_output(task_id)
            except Exception as e:
                outputs = SublimeGitException("Could not execute command: %s" % e)

        if isinstance(outputs, Exception):
            worker_logger.info("[%s,%s] got error", threading.get_ident(), task_id)
            raise outputs

        worker_logger.info("[%s,%s] got output: %s", threading.get_ident(), task_id, str(outputs)[:32])
        return outputs

    def worker_run_async(self, job, on_complete=None, on_exception=None, task_id=None):
        if not task_id:
            task_id = next_task_id()

        worker_logger.info("[%s,%s] running async task", threading.get_ident(), task_id)

        # Spawn a thread to schedule the job on the worker thread and wait for the output
        def async_inner(on_complete, on_exception, task_id):
            try:
                worker_logger.info("[%s,%s] async new input, sending...", threading.get_ident(), task_id)
                push_new_job(task_id, job)
                worker_logger.info("[%s,%s] async wait for output...", threading.get_ident(), task_id)
                outputs = get_job_output(task_id)
            except Exception as e:
                outputs = SublimeGitException("Could not execute command: %s" % e)

            if isinstance(outputs, Exception):
                worker_logger.info("[%s,%s] async got error", threading.get_ident(), task_id)
                logger.debug('async-exception: %s', outputs)
                if callable(on_exception):
                    sublime.set_timeout(partial(on_exception, outputs), 0)
            else:
                worker_logger.info("[%s,%s] async got output", threading.get_ident(), task_id)
                if callable(on_complete):
                    sublime.set_timeout(partial(on_complete, outputs), 0)

        return threading.Thread(target=partial(async_inner, on_complete, on_exception, task_id))

    # sync commands
    def cmd(self, cmd, stdin=None, cwd=None, ignore_errors=False, encoding=None, fallback=None):
        command = self.build_command(cmd)
        environment = self.env()
        encoding = encoding or get_setting('encoding', 'utf-8')
        fallback = fallback or get_setting('fallback_encodings', [])
        task_id = next_task_id()

        logger.debug("[%s,%s] cmd: %s", threading.get_ident(), task_id, command)

        def job(command, stdin, cwd, environment, ignore_errors, encoding, fallback, task_id):
            try:
                if stdin and hasattr(stdin, 'encode'):
                    stdin = stdin.encode(encoding)

                if cwd:
                    os.chdir(cwd)

                proc = subprocess.Popen(command,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        startupinfo=self.startupinfo(),
                                        env=environment)
                stdout, stderr = proc.communicate(stdin)

                logger.debug("[%s,%s] out: (%s) %s", threading.get_ident(), task_id, proc.returncode, [stdout[:100]])

                return (proc.returncode, self.decode(stdout, encoding, fallback), self.decode(stderr, encoding, fallback))
            except OSError as e:
                if ignore_errors:
                    return (0, '', '')
                sublime.error_message(self.get_executable_error())
                return SublimeGitException("[%s,%s] Could not execute command: %s" % (threading.get_ident(), task_id, e))
            except UnicodeDecodeError as e:
                if ignore_errors:
                    return (0, '', '')
                sublime.error_message(self.get_decoding_error(encoding, fallback))
                return SublimeGitException("[%s,%s] Could not execute command: %s" % (threading.get_ident(), task_id, command))

        return self.worker_run(partial(job, command, stdin, cwd, environment, ignore_errors, encoding, fallback, task_id), task_id=task_id)

    # async commands
    def cmd_async(self, cmd, cwd=None, on_data=None, on_complete=None, on_error=None, on_exception=None):
        command = self.build_command(cmd)
        environment = self.env()
        encoding = get_setting('encoding', 'utf-8')
        fallback = get_setting('fallback_encodings', [])
        task_id = next_task_id()

        logger.debug('[%s,%s] async-cmd: %s', threading.get_ident(), task_id, command)

        def job(command, cwd, encoding, on_data, task_id):
            if cwd:
                os.chdir(cwd)

            proc = subprocess.Popen(command,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    startupinfo=self.startupinfo(),
                                    env=environment)

            for line in iter(proc.stdout.readline, b''):
                logger.debug('[%s,%s] async-out: %s', threading.get_ident(), task_id, line.strip())
                line = self.decode(line, encoding, fallback)
                if callable(on_data):
                    sublime.set_timeout(partial(on_data, line), 0)

            proc.wait()
            logger.debug('[%s,%s] async-exit: %s', threading.get_ident(), task_id, proc.returncode)

            return proc.returncode

        def on_complete_inner(return_code, on_complete=None, on_error=None):
            if return_code == 0:
                if callable(on_complete):
                    sublime.set_timeout(partial(on_complete, return_code), 0)
            else:
                if callable(on_error):
                    sublime.set_timeout(partial(on_error, return_code), 0)

        return self.worker_run_async(partial(job, command, cwd, encoding, on_data, task_id),
            on_complete=partial(on_complete_inner, on_complete, on_error),
            on_exception=on_exception,
            task_id=task_id)

    # messages
    EXECUTABLE_ERROR = ("Executable '{bin}' was not found in PATH. Current PATH:\n\n"
                        "{path}\n\n"
                        "Try adjusting the git_executables['{executable}'] setting.")

    def get_executable_error(self):
        path = "\n".join(os.environ.get('PATH', '').split(':'))
        return self.EXECUTABLE_ERROR.format(executable=self.executable,
                                            path=path,
                                            bin=self.bin)

    DECODING_ERROR = ("Could not decode output from git. This means that you have a commit "
                      "message or some files in an unrecognized encoding. The following encodings "
                      "were tried:\n\n"
                      "{encodings}\n\n"
                      "Try adjusting the fallback_encodings setting.")

    def get_decoding_error(self, encoding, fallback):
        encodings = [encoding]
        if fallback:
            encodings.extend(fallback)
        return self.DECODING_ERROR.format(encodings="\n".join(encodings))


class GitCmd(GitRepoHelper, Cmd):
    executable = 'git'
    bin = ['git']
    opts = [
        '--no-pager',
        '-c', 'color.diff=false',
        '-c', 'color.status=false',
        '-c', 'color.branch=false',
        '-c', 'status.displayCommentPrefix=true',
        '-c', 'core.commentchar=#',
    ]

    def git(self, cmd, *args, **kwargs):
        return self.cmd(cmd, *args, **kwargs)

    def git_string(self, cmd, *args, **kwargs):
        return self._string(cmd, *args, **kwargs)

    def git_lines(self, cmd, *args, **kwargs):
        return self._lines(cmd, *args, **kwargs)

    def git_exit_code(self, cmd, *args, **kwargs):
        return self._exit_code(cmd, *args, **kwargs)

    def git_async(self, cmd, *args, **kwargs):
        return self.cmd_async(cmd, *args, **kwargs)


class GitFlowCmd(GitRepoHelper, Cmd):
    executable = 'git_flow'
    bin = ['git-flow']

    def git_flow(self, cmd, *args, **kwargs):
        return self.cmd(cmd, *args, **kwargs)

    def git_flow_string(self, cmd, *args, **kwargs):
        return self._string(cmd, *args, **kwargs)

    def git_flow_lines(self, cmd, *args, **kwargs):
        return self._lines(cmd, *args, **kwargs)

    def git_flow_exit_code(self, cmd, *args, **kwargs):
        return self._exit_code(cmd, *args, **kwargs)

    def git_flow_async(self, cmd, *args, **kwargs):
        return self.cmd_async(cmd, *args, **kwargs)


class LegitCmd(GitRepoHelper, Cmd):
    executable = 'legit'
    bin = ['legit']

    def legit(self, cmd, *args, **kwargs):
        return self.cmd(cmd, *args, **kwargs)

    def legit_string(self, cmd, *args, **kwargs):
        return self._string(cmd, *args, **kwargs)

    def legit_lines(self, cmd, *args, **kwargs):
        return self._lines(cmd, *args, **kwargs)

    def legit_exit_code(self, cmd, *args, **kwargs):
        return self._exit_code(cmd, *args, **kwargs)

    def legit_async(self, cmd, *args, **kwargs):
        return self.cmd_async(cmd, *args, **kwargs)
