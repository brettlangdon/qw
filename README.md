qw
==

qw (or QueueWorker) is used to run worker processes which listen on a redis list for jobs to process.

## Setup
### pip

`pip install qw`

### git

```
git clone git://github.com/brettlangdon/qw.git
cd ./qw
python setup.py install
```

## Design
### Manager
The manager is simply a process manager. It's job is to start/stop worker sub-processes.

### Worker
The workers are processes which sit and listen for jobs on a few queues and then process
those jobs.

### Target
The worker/manager take a `target` which can be either a function or a string (importable function).

```python
def target(job_id, job_data):
    pass

manager = Manager(target)
# OR
manager = Manager('__main__.target')
```
### Queues
There are a few different queues that are used. The job queues are just redis lists, manager/worker lists are sets and jobs are hashes.

A worker picks up a job from either `all:jobs`, `<manager>:jobs` or `<worker>:jobs`, pulls the corresponding `job:<job_id>` key and
processes it with the provided `target`, after processing it will then remove the `job:<job_id>` key as well as the job id from
the `<worker>:jobs` queue.

* `all:managers` - a set of all managers
* `all:jobs` - a queue that all workers can pull jobs from, the values are just the job ids
* `job:<job_id>` - a hash of the job data
* `<manager>:workers` - a set of all workers belonging to a given manager
* `<manager>:jobs` - a queue of jobs for a specific manager, workers will try to pull from here before `all:jobs`, the values are just the job ids
* `<worker>:jobs` - a queue of jobs for a specific worker, this is meant as a in progress queue for each worker, the workers will pull jobs into this queue from either `<manager>:jobs` or `all:jobs`, the values are just the job ids

## Basic Usage

```python
from qw.manager import Manager


def job_printer(job_id, job_data):
    print job_id
    print job_data


manager = Manager(job_printer)
manager.start()
manager.join()
```

## API
### Manager(object)
* `__init__(self, target, host="localhost", port=6379, db=0, num_workers=None, name=None)`
* `start(self)`
* `stop(self)`
* `join(self)`

### Worker(multiprocess.Process)
* `__init__(self, client, target, manager_name=None, timeout=10)`
* `run(self)`
* `shutdown(self)`

### Client(redis.StrictRedi)
* `__init__(self, host="localhost", port=6379, db=0)`
* `register_manager(self, name)`
* `deregister_manager(self, name)`
* `register_worker(self, manager, name)`
* `deregister_worker(self, manager, name)`
* `queue_job(self, job_data, manager=None, worker=None)`
* `fetch_next_job(self, manager, worker, timeout=10)`
* `finish_job(self, job_id, worker_name)`
* `get_all_managers(self)`
* `get_manager_workers(self, manager_name)`
* `get_worker_pending_jobs(self, worker_name)`
* `get_manager_queued_jobs(self, manager_name)`
* `get_all_queued_jobs(self)`
* `get_all_pending_jobs(self)`

## CLI Tools
### qw-manager
The `qw-manager` tool is used to start a new manager process with the provided `target` string, which gets run
for every job processed by a worker.
```
$ qw-manager --help
Usage:
  qw-manager [--level=<log-level>] [--workers=<num-workers>] [--name=<name>] [--host=<host>] [--port=<port>] [--db=<db>] <target>
  qw-manager (--help | --version)

Options:
  --help                       Show this help message
  --version                    Show version information
  -l --level=<log-level>       Set the log level (debug,info,warn,error) [default: info]
  -w --workers=<num-workers>   Set the number of workers to start, defaults to number of cpus
  -n --name=<name>             Set the manager name, defaults to hostname
  -h --host=<host>             Set the redis host to use [default: localhost]
  -p --port=<port>             Set the redis port to use [default: 6379]
  -d --db=<db>                 Set the redis db number to use [default: 0]
```
### qw-client
The `qw-client` command is useful to look at basic stats of running managers, workers and job queues
as well as to push json data in the form of a string or a file to the main queue or a manager specific queue.
```
$ qw-client --help
Usage:
  qw-client [--host=<host>] [--port=<port>] [--db=<db>] managers
  qw-client [--host=<host>] [--port=<port>] [--db=<db>] workers [<manager>]
  qw-client [--host=<host>] [--port=<port>] [--db=<db>] jobs [<manager>]
  qw-client [--host=<host>] [--port=<port>] [--db=<db>] queue string <data> [<manager>]
  qw-client [--host=<host>] [--port=<port>] [--db=<db>] queue file <file> [<manager>]
  qw-client (--help | --version)

Options:
  --help                       Show this help message
  --version                    Show version information
  -h --host=<host>             Set the redis host to use [default: localhost]
  -p --port=<port>             Set the redis port to use [default: 6379]
  -d --db=<db>                 Set the redis db number to use [default: 0]
```
