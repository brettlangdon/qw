import redis

import uuid


class Client(redis.StrictRedis):
    ALL_MANAGERS = "all:managers"
    ALL_JOBS = "all:jobs"
    MANAGER_WORKERS = "%s:workers"
    MANAGER_JOBS = "%s:jobs"
    WORKER_JOBS = "%s:jobs"
    JOB_KEY = "job:%s"

    def __init__(self, host="localhost", port=6379, db=0):
        super(Client, self).__init__(host=host, port=port, db=db)

    def register_manager(self, name):
        self.sadd(self.ALL_MANAGERS, name)

    def deregister_manager(self, name)    :
        self.srem(self.ALL_MANAGERS, name)

    def register_worker(self, manager, name):
        self.sadd(self.MANAGER_WORKERS % (manager, ), name)

    def deregister_worker(self, manager, name):
        self.srem(self.MANAGER_WORKERS % (manager, ), name)

    def queue_job(self, job_data, manager=None, worker=None):
        job_id = uuid.uuid4()
        self.hmset(self.JOB_KEY % (job_id, ), job_data)
        if manager is not None:
            self.lpush(self.MANAGER_JOBS % (manager, ), job_id)
        elif worker is not None:
            self.lpush(self.WORKER_JOBS % (worker, ), job_id)
        else:
            self.lpush(self.ALL_JOBS, job_id)

        return job_id

    def fetch_next_job(self, manager, worker, timeout=10):
        # try to fetch in this order
        #  1) any jobs already assigned but not finished by the worker
        #  2) any jobs assigned specifically to the manager
        #  3) try to grab a job from the pool of all jobs
        job_id = (
            self.lpop(self.WORKER_JOBS % (worker, )) or
            self.rpoplpush(self.MANAGER_JOBS % (manager, ), self.WORKER_JOBS % (worker, )) or
            self.brpoplpush(self.ALL_JOBS, self.WORKER_JOBS % (worker, ), timeout=timeout)
        )

        job_data = None
        if job_id is not None:
            job_data = self.hgetall(self.JOB_KEY % (job_id, ))

        return (job_id, job_data)

    def finish_job(self, job_id, worker_name):
        self.delete(self.JOB_KEY % (job_id, ))
        self.lrem(self.WORKER_JOBS % (worker_name, ), 1, job_id)

    def get_all_managers(self):
        return self.smembers(self.ALL_MANAGERS)

    def get_manager_workers(self, manager_name):
        return self.smembers(self.MANAGER_WORKERS % (manager_name, ))

    def get_worker_pending_jobs(self, worker_name):
        for job_id in self.lrange(self.WORKER_JOBS % (worker_name, ), 0, -1):
            yield job_id

    def get_manager_queued_jobs(self, manager_name):
        for job_id in self.lrange(self.MANAGER_JOBS % (manager_name, ), 0, -1):
            yield job_id

    def get_all_queued_jobs(self):
        for job_id in self.lrange(self.ALL_JOBS, 0, -1):
            yield (None, job_id)

        for manager in self.get_all_managers():
            for job_id in self.get_manager_queued_jobs(manager):
                yield (manager, job_id)

    def get_all_pending_jobs(self):
        for manager in self.get_all_managers():
            for worker in self.get_manager_workers(manager):
                for job_id in self.get_worker_pending_jobs(worker):
                    yield (worker, job_id)
