#!/bin/bash
set -e

echo 'INFO: database cleanup'
sh bin/server_make_db.sh 1>/dev/null 2>/dev/null
for all in $(sh bin/server_command.sh scheduler task_list | awk '{print $1}' | grep -v id); do
	sh bin/server_command.sh scheduler task_delete $all
done


echo -n 'INFO: task add: '
TESTNET="$(seq 1 3 | xargs -I{} printf '10.%d.0.0/16 ' {})"
time sh -c "(sh bin/server_command.sh scheduler enumips $TESTNET | sh bin/server_command.sh scheduler task_add 1 --file - --name 'testnet' --group_size 100)"


echo -n 'INFO: task list: '
time sh bin/server_command.sh scheduler task_list 1>/dev/null


echo -n 'INFO: task schedule: '
time sh bin/server_command.sh scheduler task_targets 3 schedule


echo -n 'INFO: job/assign: '
time curl -o /dev/null -s http://localhost:18000/scheduler/job/assign/3
