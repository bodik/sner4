#!/bin/sh

if [ "${GIT_AUTHOR_NAME}" = "root" ]; then
	echo "ERROR: not allowed to commit as root"
	exit 1
fi
