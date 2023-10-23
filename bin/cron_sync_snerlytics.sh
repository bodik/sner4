#!/bin/sh
# snerlytics cron helper

/opt/sner/venv/bin/python /opt/sner/bin/server storage sync-storage
/opt/sner/venv/bin/python /opt/sner/bin/server storage rebuild-vulnsearch-elastic
