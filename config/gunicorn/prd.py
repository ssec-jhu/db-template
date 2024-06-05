"""Gunicorn *production* config file"""

import multiprocessing
import os

# Django WSGI application path in pattern MODULE_NAME:VARIABLE_NAME
wsgi_app = "biodb.wsgi:application"

# The socket to bind
bind = f"0.0.0.0:{os.getenv('HOST_PORT', 8000)}"

# The granularity of Error log outputs
loglevel = os.getenv("DJANGO_LOG_LEVEL", "INFO")

# The number of worker processes for handling requests.
# Note: this is multiprocessing and not multithreading, because the GIL.
workers = os.getenv("N_WORKERS", multiprocessing.cpu_count())
worker_class = "sync"

# Note: If you try to use the sync worker type and set the threads setting to more than 1, the gthread worker class will
# be used instead.
threads = os.getenv("N_THREADS", 1)  # Run each worker with this specified number of threads.

# Restart workers when code changes (development only!)
reload = False

# The maximum number of requests a worker will process before restarting (mitigates memory leaks).
max_requests = 10000
max_requests_jitter = int(max_requests * 0.01)  # 1% of max_requests.

# Workers silent for more than this many seconds are killed and restarted.
timeout = 60
# After receiving a restart signal, workers have this much time to finish serving requests.
graceful_timeout = 30

# Write access and error info to:
# accesslog = "log/prd_access.log"
# errorlog = "log/prd_error.log"

# Redirect stdout/stderr to log file
capture_output = False

# PID file so you can easily fetch process ID
# pidfile = "run/prd.pid"

# Daemonize the Gunicorn process (detach & enter background)
daemon = False
