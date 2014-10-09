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
