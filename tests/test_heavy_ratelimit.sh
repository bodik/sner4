#!/bin/bash
# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.

SERVER=$1

APIKEY=$(bin/server auth add-agent | rev | awk '{print $1}' | rev)
while true; do time curl -XPOST -H "X-API-KEY: $APIKEY" "${SERVER}/api/v2/scheduler/job/assign" | grep '{}' && break; done
