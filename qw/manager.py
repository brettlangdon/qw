import logging
import multiprocessing
import socket

import redis

from qw import queue_name
from qw.exception import AlreadyStartedException, NotStartedException
from qw.worker import Worker


class Manager(object):
    __slots__ = ["workers", "connection", "num_workers", "log", "name"]

    def __init__(self, host="localhost", port=6379, db=0, num_workers=None, name=None):
        self.workers = []
        self.num_workers = num_workers or multiprocessing.cpu_count()
        self.connection = redis.StrictRedis(host=host, port=port, db=db)
        self.log = logging.getLogger("qw.manager")
        self.name = name or socket.gethostname()

    def start(self):
        self.log.info("starting", extra={"process_name": self.name})
        if self.workers:
            raise AlreadyStartedException("Workers Already Started")

        self.log.info("starting %s workers", self.num_workers, extra={"process_name": self.name})
        for _ in xrange(self.num_workers):
            worker = Worker(self.connection, manager_name=self.name)
            worker.start()
            self.workers.append(worker)
        self.log.info("registering %s under %s", self.name, queue_name.ALL_MANAGERS, extra={"process_name": self.name})
        self.connection.sadd(queue_name.ALL_MANAGERS, self.name)

    def join(self):
        self.log.debug("joining workers", extra={"process_name": self.name})
        if not self.workers:
            raise NotStartedException("Workers Do Not Exist")

        # wait for them all to stop
        for worker in self.workers:
            worker.join()

        # make sure to clear out workers list
        self.workers = []

    def stop(self):
        self.log.info("stopping", extra={"process_name": self.name})
        if not self.workers:
            raise NotStartedException("Workers Do Not Exist")

        self.log.info("deregistering %s from %s", self.name, queue_name.ALL_MANAGERS, extra={"process_name": self.name})
        self.connection.srem(queue_name.ALL_MANAGERS, self.name)

        self.log.info("shutting down %s workers", len(self.workers), extra={"process_name": self.name})
        # trigger them all to shutdown
        for worker in self.workers:
            worker.shutdown()

        self.join()
        self.log.info("stopped", extra={"process_name": self.name})

    def get_worker_pending_jobs(self):
        if not self.workers:
            raise NotStartedException("Workers Do Not Exist")

        worker_names = self.connection.smembers("%s:workers" % (self.name, ))

        for worker_name in worker_names:
            self.log.debug("fetching %s's pending jobs", worker_name, extra={"process_name": self.name})
            for job in self.connection.lrange("%s:jobs" % (worker_name, ), 0, -1):
                yield (worker_name, job)

    def get_all_queued_jobs(self):
        return self.connection.lrange(queue_name.ALL_JOBS, 0, -1)
