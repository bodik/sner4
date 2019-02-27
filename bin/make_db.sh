#!/bin/sh
set -e

#su -c 'psql --command="CREATE ROLE root WITH LOGIN;"' postgres
#su -c 'psql --command="CREATE DATABASE sner OWNER root;"' postgres
psql --command="SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='sner';" postgres
psql -t --command="SELECT 'drop table '||tablename||' cascade;' FROM pg_tables WHERE schemaname='public';" sner | psql sner

bin/server.sh db init
bin/server.sh db initdata
