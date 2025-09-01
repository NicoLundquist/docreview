# Gunicorn configuration file
bind = "0.0.0.0:5000"
workers = 1
timeout = 1200  # 20 minutes timeout for large document processing and file uploads
client_timeout = 1200  # 20 minutes for client connections
reload = True
accesslog = "-"
errorlog = "-"
loglevel = "info"
max_requests = 1000
max_requests_jitter = 50
worker_connections = 1000