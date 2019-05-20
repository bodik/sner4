#!/bin/sh

. tests/common.sh
TESTID="agent_test_processhandling_$(date +%s)"


# add task, queue and target
bin/server scheduler task_add nmap --name ${TESTID} --params '-Pn --reason -sU --max-rate 1'
bin/server scheduler queue_add ${TESTID} --name ${TESTID}
bin/server scheduler queue_enqueue ${TESTID} "127.126.125.124"


bin/agent --debug --queue ${TESTID} --oneshot &
PID=$!
sleep 1

bin/agent --terminate ${PID}
sleep 3

pgrep --full "127.126.125.124"
if [ $? -eq 0 ]; then
	rreturn 1 "child process left running"
fi
ps -p ${PID} 1>/dev/null
if [ $? -eq 0 ]; then
	rreturn 1 "agent still running"
fi


# cleanup test data 
JOBID=$(bin/server scheduler job_list | grep ${TESTID} | awk '{print $1}')
bin/server scheduler job_delete ${JOBID}
bin/server scheduler queue_delete ${TESTID}
bin/server scheduler task_delete ${TESTID}

rreturn 0 $0
