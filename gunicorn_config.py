# Gunicorn configuration file
bind = "0.0.0.0:5000"
workers = 1
timeout = 600  # 10 minutes timeout for large document processing
reload = True
accesslog = "-"
errorlog = "-"
loglevel = "info"