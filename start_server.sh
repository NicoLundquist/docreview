#!/bin/bash
# Start Gunicorn with extended timeout for GPT-5 processing of large documents
exec gunicorn --bind 0.0.0.0:5000 --timeout 600 --workers 1 --reload main:app