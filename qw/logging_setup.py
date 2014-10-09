import logging

FORMAT = "%(asctime)s - %(name)s - %(process_name)s - %(levelname)s - %(message)s"
formatter = logging.Formatter(FORMAT)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

manager_logger = logging.getLogger("qw.manager")
manager_logger.addHandler(stream_handler)

worker_logger = logging.getLogger("qw.worker")
worker_logger.addHandler(stream_handler)
