#!/bin/sh

. tests/common.sh
TESTID="agent_test_dummy_$(date +%s)"


# add dummy task, dummy queue
bin/server.sh scheduler task_add dummy --name ${TESTID} --params '--dummyparam 1'
bin/server.sh scheduler queue_add ${TESTID} --name ${TESTID}
bin/server.sh scheduler queue_enqueue ${TESTID} "${TESTID}_target"


bin/agent --debug --queue ${TESTID} --oneshot
if [ $? -ne 0 ]; then
	rreturn 1 'agent failed'
fi

JOBID=$(bin/server.sh scheduler job_list | grep ${TESTID} | awk '{print $1}')
unzip -p var/scheduler/${JOBID} ${JOBID}/assignment.json | grep -q -- "--dummyparam 1"
if [ $? -ne 0 ]; then
	rreturn 1 'agent output failed'
fi


# cleanup test data 
bin/server.sh scheduler job_delete ${JOBID}
bin/server.sh scheduler queue_delete ${TESTID}
bin/server.sh scheduler task_delete ${TESTID}

rreturn 0 $0
