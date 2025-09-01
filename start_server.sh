#!/bin/bash
# Start Gunicorn with extended timeout for GPT-5 processing of large documents and file uploads
exec gunicorn --bind 0.0.0.0:5000 --timeout 1200 --workers 1 --reload --max-requests 1000 --max-requests-jitter 50 main:app