#!/bin/bash

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$PROJECT_ROOT"

echo "Starting deploy..."

# 1. Pull latest code
git pull origin main

# 2. Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 3. Install dependencies
pip install -r requirements.txt

# 4. Apply migrations
python manage.py migrate

# 5. Collect static files
python manage.py collectstatic --noinput

# 6. Restart application (Adjust according to your server setup, e.g., Supervisor, Systemd, Docker)
# sudo systemctl restart statsfut2
# OR
# docker-compose restart web

echo "Deploy finished successfully!"
