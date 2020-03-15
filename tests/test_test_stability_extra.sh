#!/bin/sh
# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.

for iter in $(seq 1 100); do
	timeout 600 make test-extra
	RET=$?
	echo "INFO: round ${iter}"
	if [ $RET -ne 0 ]; then
		echo "ERROR: error"
		exit
	fi
done