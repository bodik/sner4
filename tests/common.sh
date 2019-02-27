#!/bin/sh

rreturn() {
	RET=$1; shift

	if [ $RET -eq 0 ]; then
		echo "RESULT: OK $@"
		exit 0
	fi

	echo "RESULT: FAILED $@"
	exit 1
}
