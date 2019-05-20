#!/bin/sh

. tests/common.sh
TESTID="agent_test_dummy_$(date +%s)"


# add dummy task, dummy queue
bin/server scheduler task_add dummy --name ${TESTID} --params '--dummyparam 1'
bin/server scheduler queue_add ${TESTID} --name ${TESTID}
bin/server scheduler queue_enqueue ${TESTID} "${TESTID}_target"


bin/agent --debug --queue ${TESTID} --oneshot
if [ $? -ne 0 ]; then
	rreturn 1 'agent failed'
fi

OUTPUT_FILENAME=$(bin/server scheduler job_list | grep ${TESTID} | awk '{print $6}')
unzip -p ${OUTPUT_FILENAME} assignment.json | grep -q -- "--dummyparam 1"
if [ $? -ne 0 ]; then
	rreturn 1 'agent output failed'
fi


# cleanup test data 
JOBID=$(bin/server scheduler job_list | grep ${TESTID} | awk '{print $1}')
bin/server scheduler job_delete ${JOBID}
bin/server scheduler queue_delete ${TESTID}
bin/server scheduler task_delete ${TESTID}

rreturn 0 $0
