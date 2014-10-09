import logging
import multiprocessing
import socket

from qw.client import Client
from qw.exception import AlreadyStartedException, NotStartedException
from qw.worker import Worker


class Manager(object):
    __slots__ = ["workers", "client", "num_workers", "log", "name", "target"]

    def __init__(self, target, host="localhost", port=6379, db=0, num_workers=None, name=None):
        self.workers = []
        self.num_workers = num_workers or multiprocessing.cpu_count()
        self.client = Client(host=host, port=port, db=db)
        self.log = logging.getLogger("qw.manager")
        self.name = name or socket.gethostname()
        self.target = target

    def start(self):
        self.log.info("starting", extra={"process_name": self.name})
        if self.workers:
            raise AlreadyStartedException("Workers Already Started")

        self.log.info("starting %s workers", self.num_workers, extra={"process_name": self.name})
        for _ in xrange(self.num_workers):
            worker = Worker(self.client, self.target, manager_name=self.name)
            worker.start()
            self.workers.append(worker)
        self.log.info("registering %s", self.name, extra={"process_name": self.name})
        self.client.register_manager(self.name)

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

        self.log.info("deregistering %s", self.name, extra={"process_name": self.name})
        self.client.deregister_manager(self.name)

        self.log.info("shutting down %s workers", len(self.workers), extra={"process_name": self.name})
        # trigger them all to shutdown
        for worker in self.workers:
            worker.shutdown()

        self.join()
        self.log.info("stopped", extra={"process_name": self.name})
