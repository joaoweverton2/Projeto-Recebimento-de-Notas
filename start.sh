#!/usr/bin/env bash

# Start Gunicorn with 4 workers, binding to 0.0.0.0 on port 10000
# The port 10000 is a common default for Render, but check Render's documentation for the exact port.
# The $PORT environment variable is automatically set by Render.
exec gunicorn --bind 0.0.0.0:$PORT --workers 4 main:app


