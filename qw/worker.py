import logging
import multiprocessing
import time
import traceback
import socket
import os

from qw import queue_name


class Worker(multiprocessing.Process):
    __slots__ = [
        "connection", "exit", "log", "timeout", "manager_name"
    ]

    def __init__(self, redis_connection, manager_name=None, timeout=10):
        super(Worker, self).__init__()
        self.connection = redis_connection
        self.manager_name = manager_name or socket.gethostname()
        self.exit = multiprocessing.Event()
        self.timeout = timeout
        self.log = logging.getLogger("qw.worker")

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
        # reigtser this process under the parent manager_name
        self.connection.sadd("%s:workers" % (self.manager_name, ), self.name)

    def _deregister(self):
        self.log.info(
            "deregistering worker %s from '%s:workers'" % (self.name, self.manager_name),
            extra={"process_name": self.name}
        )
        self.connection.srem("%s:workers" % (self.manager_name, ), self.name)

    def _run(self):
        # try to fetch a previously unfinished job
        # otherwise try to fetch from the main job pool
        self.log.debug(
            "polling for jobs from '%s' and '%s'" % (self.job_queue, queue_name.ALL_JOBS),
            extra={"process_name": self.name}
        )
        job_id = (
            self.connection.lpop(self.job_queue) or
            self.connection.brpoplpush(queue_name.ALL_JOBS, self.job_queue, timeout=self.timeout)
        )

        if not job_id:
            self.log.debug(
                "no jobs found from '%s' or '%s'" % (self.job_queue, queue_name.ALL_JOBS),
                extra={"process_name": self.name}
            )
            return

        job_data = self.connection.hgetall("job:%s" % (job_id, ))
        self.log.debug(
            "processing job id (%s) data (%r)" % (job_id, job_data), extra={"process_name": self.name}
        )
        if job_data:
            self._process(job_id, job_data)

        self.log.debug("removing job id (%s)" % (job_id), extra={"process_name": self.name})
        self.connection.delete("job:%s" % (job_id, ))
        self.connection.lrem(self.job_queue, 1, job_id)

    def _process(self, job_id, job_data):
        print "%s - %s" % (job_id, job_data)
        time.sleep(20)
        print "done"

    def run(self):
        self.log.info("starting", extra={"process_name": self.name})
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
