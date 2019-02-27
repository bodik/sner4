#!/bin/sh

TESTID="agent_test_dummy_$(date +%s)"

# add dummy task, dummy queue
bin/server_command.sh scheduler task_add dummy --name ${TESTID} --params '--dummyparam 1'
bin/server_command.sh scheduler queue_add ${TESTID} --name ${TESTID}
bin/server_command.sh scheduler queue_enqueue ${TESTID} "${TESTID}_target"


# run the agent
sh bin/agent_run.sh --debug --queue ${TESTID}
echo "RESULT: $?"
bin/server_command.sh scheduler job_list


# check the output on the server
bin/server_command.sh scheduler queue_delete ${TESTID}
bin/server_command.sh scheduler task_delete ${TESTID}
