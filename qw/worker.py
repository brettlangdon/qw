import logging
import multiprocessing
import traceback
import socket
import os

from qw.utils import dynamic_import


class Worker(multiprocessing.Process):
    __slots__ = [
        "client", "exit", "log", "timeout", "manager_name", "target"
    ]

    def __init__(self, client, target, manager_name=None, timeout=10):
        super(Worker, self).__init__()
        self.client = client
        self.manager_name = manager_name or socket.gethostname()
        self.exit = multiprocessing.Event()
        self.timeout = timeout
        self.log = logging.getLogger("qw.worker")
        self.target = target

    @property
    def name(self):
        return "%s.%s" % (self.manager_name, os.getpid())

    @property
    def job_queue(self):
        return "%s:jobs" % (self.name, )

    def _register(self):
        self.log.info(
            "registering worker %s under '%s:workers'" % (self.name, self.manager_name),
            extra={"process_name": self.name}
        )
        self.client.register_worker(self.manager_name, self.name)

    def _deregister(self):
        self.log.info(
            "deregistering worker %s from '%s:workers'" % (self.name, self.manager_name),
            extra={"process_name": self.name}
        )
        self.client.deregister_worker(self.manager_name, self.name)

    def _run(self):
        # try to fetch a previously unfinished job
        # otherwise try to fetch from the main job pool
        self.log.debug("polling for jobs", extra={"process_name": self.name})
        job_id, job_data = self.client.fetch_next_job(self.manager_name, self.name, timeout=self.timeout)
        if not job_id or not job_data:
            return

        self.log.debug(
            "processing job id (%s) data (%r)" % (job_id, job_data), extra={"process_name": self.name}
        )
        if job_data:
            self.target(job_id, job_data)

        self.log.debug("removing job id (%s)" % (job_id), extra={"process_name": self.name})
        self.client.finish_job(job_id, self.name)

    def run(self):
        self.log.info("starting", extra={"process_name": self.name})
        if isinstance(self.target, basestring):
            self.target = dynamic_import(self.target)
        self._register()
        while not self.exit.is_set():
            try:
                self._run()
            except KeyboardInterrupt:
                self.log.error("encountered a KeyboardInterrupt", extra={"process_name": self.name})
                break
            except Exception, e:
                self.log.error("encountered an error (%r)" % (e, ), extra={"process_name": self.name})
                traceback.print_exc()

        self._deregister()
        self.log.info("stopping", extra={"process_name": self.name})

    def shutdown(self):
        self.log.info("shutdown signal received", extra={"process_name": self.name})
        self.exit.set()
