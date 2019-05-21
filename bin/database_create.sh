#!/bin/sh
# postgres helper

DBNAME="sner"
if [ -n "$1" ]; then
	DBNAME="$1"
fi

ROLE="${USER}"
if [ -n "$2" ]; then
	ROLE="$2"
fi


psql --dbname postgres --command "
	DO \$\$
	BEGIN
		CREATE ROLE ${ROLE} WITH LOGIN;
	EXCEPTION WHEN OTHERS THEN
		RAISE NOTICE 'role ${ROLE} already exists';
	END \$\$;"

psql --dbname postgres --command "
	DO \$\$
	BEGIN
		CREATE EXTENSION IF NOT EXISTS dblink;
		PERFORM dblink_exec('', 'CREATE DATABASE ${DBNAME}');
	EXCEPTION WHEN duplicate_database THEN
		RAISE NOTICE 'database ${DBNAME} already exist';
	END \$\$;"
