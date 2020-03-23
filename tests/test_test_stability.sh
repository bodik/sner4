#!/bin/sh
# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
#
# test the stability of the tests

for iter in $(seq 1 100); do
	timeout 600 make coverage
	RET=$?
	echo "INFO: round ${iter}"
	if [ $RET -eq 124 ]; then
		echo "ERROR: timedout"
		exit
	fi
	if [ $RET -ne 0 ]; then
		echo "ERROR: error"
		exit
	fi
done
