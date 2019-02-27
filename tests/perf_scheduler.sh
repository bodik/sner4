#!/bin/bash
set -e


ITERATIONS=4
if [ -n "$1" ]; then
	ITERATIONS=$1
fi


echo 'INFO: database cleanup'
sh bin/server_make_db.sh 1>/dev/null 2>/dev/null
for all in $(sh bin/server_command.sh scheduler task_list | awk '{print $1}' | grep -v id); do
	sh bin/server_command.sh scheduler task_delete $all
done


for iter in $(seq 1 ${ITERATIONS}); do
	echo "INFO: test iteration ${iter}"
	echo -en "INFO: task add: \t\t"
	TESTNET=$(printf '10.%d.0.0/16 11.%d.0.0/16 12.%d.0.0/16' ${iter} ${iter} ${iter})
	(time sh -c "(sh bin/server_command.sh scheduler enumips ${TESTNET} | sh bin/server_command.sh scheduler task_add 1 --file - --name 'testnet' --group_size 100)") 2>&1 | grep real

	echo -en "INFO: task list: \t\t"
	(time sh bin/server_command.sh scheduler task_list 1>/dev/null) 2>&1 | grep real

	echo -en "INFO: task schedule: \t\t"
	(time sh bin/server_command.sh scheduler task_targets $((2+${iter})) schedule) 2>&1 | grep real

	echo -en "INFO: job/assign: \t\t"
	(time curl -o /dev/null -s http://localhost:18000/scheduler/job/assign/3) 2>&1 | grep real
done
