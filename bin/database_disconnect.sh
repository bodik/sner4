#!/bin/sh
# postgres helper

DBNAME="sner"
if [ -n "$1" ]; then
	DBNAME="$1"
fi

psql --command="SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DBNAME}';"
