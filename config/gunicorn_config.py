# gunicorn config

bind = "0.0.0.0:18080"
workers = 2
timeout = 120
backlog = 2048
worker_class = "eventlet"
worker_connections = 1000
daemon = False