#!/bin/sh

. tests/common.sh
TESTID="agent_test_nmap_$(date +%s)"

# add test task, queue and target
bin/server scheduler task_add nmap --name ${TESTID} --params '-sL'
bin/server scheduler queue_add ${TESTID} --name ${TESTID}
bin/server scheduler queue_enqueue ${TESTID} "127.0.0.1"


bin/agent --debug --queue ${TESTID} --oneshot
if [ $? -ne 0 ]; then
	rreturn 1 'agent failed'
fi

JOBID=$(bin/server scheduler job_list | grep ${TESTID} | awk '{print $1}')
unzip -p var/scheduler/${JOBID} output.gnmap | grep -q 'Host: 127.0.0.1 (localhost)'
if [ $? -ne 0 ]; then
	rreturn 1 'agent output failed'
fi


# cleanup test data 
bin/server scheduler job_delete ${JOBID}
bin/server scheduler queue_delete ${TESTID}
bin/server scheduler task_delete ${TESTID}

rreturn 0 $0
