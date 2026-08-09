#!/bin/bash
cd /www/wwwroot/statsfut.com
source /www/wwwroot/statsfut.com/venv/bin/activate
exec gunicorn -c /www/wwwroot/statsfut.com/gunicorn_config.py
