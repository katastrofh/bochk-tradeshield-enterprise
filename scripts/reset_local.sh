#!/usr/bin/env bash
set -euo pipefail
sudo docker compose down -v --remove-orphans
sudo docker compose build --no-cache app
sudo docker compose up
