#!/bin/bash
# Start Gunicorn with extended timeout for GPT-5 processing
exec gunicorn --bind 0.0.0.0:5000 --reuse-port --reload --timeout 300 --workers 1 main:app