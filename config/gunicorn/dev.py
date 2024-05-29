"""Gunicorn *development* config file"""

# Django WSGI application path in pattern MODULE_NAME:VARIABLE_NAME
wsgi_app = "biodb.wsgi:application"

# The socket to bind
bind = "0.0.0.0:8000"

# The granularity of Error log outputs
loglevel = "debug"

# The number of worker processes for handling requests
workers = 1
worker_class = "sync"

# Restart workers when code changes (development only!)
reload = True

# Write access and error info to:
accesslog = errorlog = "log/dev.log"

# Redirect stdout/stderr to log file
capture_output = True

# PID file so you can easily fetch process ID
pidfile = "run/dev.pid"

# Daemonize the Gunicorn process (detach & enter background)
daemon = False
