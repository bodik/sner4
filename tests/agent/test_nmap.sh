#!/bin/sh

. tests/agent/lib.sh
testserver_create


bin/server scheduler task_add nmap --name test_task --params '-sL'
bin/server scheduler queue_add test_task --name test_queue
bin/server scheduler queue_enqueue test_queue "127.0.0.1"


bin/agent --server 'http://localhost:19000' --debug --queue test_queue --oneshot
if [ $? -ne 0 ]; then
	testserver_cleanup
	rreturn 1 'agent failed'
fi

OUTPUT_FILENAME=$(bin/server scheduler job_list | tail -1 | awk '{print $6}')
unzip -p ${OUTPUT_FILENAME} output.gnmap | grep -q 'Host: 127.0.0.1 (localhost)'
if [ $? -ne 0 ]; then
	testserver_cleanup
	rreturn 1 'agent output failed'
fi


testserver_cleanup
rreturn 0 $0
