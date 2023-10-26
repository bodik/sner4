#!/bin/sh
# snerlytics cron helper

/opt/sner/venv/bin/python /opt/sner/bin/server storage rebuild-elasticstorage
/opt/sner/venv/bin/python /opt/sner/bin/server storage rebuild-vulnsearch-localdb
/opt/sner/venv/bin/python /opt/sner/bin/server storage rebuild-vulnsearch-elastic
