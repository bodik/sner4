#!/bin/sh

rreturn() {
	RET=$1; shift

	if [ $RET -eq 0 ]; then
		echo "RESULT: OK $@"
	else
		echo "RESULT: FAILED $@"
	fi
	exit $RET
}


testserver_cleanup() {
	export SNER_CONFIG='tests/sner.yaml'

	kill -TERM ${SNER_TEST_SERVER_PID}
	wait ${SNER_TEST_SERVER_PID}
	bin/server db remove
}


testserver_create() {
	export SNER_CONFIG='tests/sner.yaml'

	bin/server db remove
	bin/server db init
	bin/server run --port 19000 1>/dev/null 2>/dev/null & 
	export SNER_TEST_SERVER_PID=$!
	trap testserver_cleanup INT

	curl --silent --fail --retry-connrefused --retry 3 --max-time 30 'http://localhost:19000' 1>/dev/null
	if [ $? -ne 0 ]; then
		rreturn 1 "$0 failed to start test server"
	fi
}
