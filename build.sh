#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install production dependencies
pip install -r requirements.txt

# Collect static assets into staticfiles directory
python manage.py collectstatic --no-input

# Run database schema migrations
python manage.py migrate

# Seed default donation categories
python manage.py seed_categories
