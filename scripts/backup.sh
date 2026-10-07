#!/bin/sh
# Linux / macOS backup. For a daily backup at 6 pm add to crontab:
# 0 18 * * * /path/to/library-system/scripts/backup.sh
cd "$(dirname "$0")/.." || exit 1
mkdir -p backups
FILE="backups/library_$(date +%Y-%m-%d_%H%M).sql"
docker compose exec -T db pg_dump -U library -d library > "$FILE"
echo "Backup saved to $FILE"
