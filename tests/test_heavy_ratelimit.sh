#!/bin/bash
# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.

APIKEY=$(bin/server auth add-agent | rev | awk '{print $1}' | rev)
while true; do time curl -H "Authorization: Apikey $APIKEY" http://localhost:18000/api/scheduler/job/assign | grep '{}' && break; done
