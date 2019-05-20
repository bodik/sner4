#!/bin/sh

. tests/agent/lib.sh
testserver_create


# add task, queue and target
bin/server scheduler task_add nmap --name test_task --params '-Pn --reason -sU --max-rate 1'
bin/server scheduler queue_add test_task --name test_queue
bin/server scheduler queue_enqueue test_queue "127.126.125.124"


bin/agent --server 'http://localhost:19000' --debug --queue test_queue --oneshot &
PID=$!
sleep 1

bin/agent --terminate ${PID}
sleep 3

pgrep --full "127.126.125.124"
if [ $? -eq 0 ]; then
	testserver_cleanup
	rreturn 1 "child process left running"
fi
ps -p ${PID} 1>/dev/null
if [ $? -eq 0 ]; then
	testserver_cleanup
	rreturn 1 "agent still running"
fi


testserver_cleanup
rreturn 0 $0
