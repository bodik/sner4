#!/bin/sh

#https://www.dan.me.uk/bgplookup?asn=2852
CESNET2_IPV4="146.102.0.0/16 147.228.0.0/16 147.230.0.0/15 147.251.0.0/16 147.32.0.0/15 158.194.0.0/16 158.196.0.0/16 160.216.0.0/15 185.8.160.0/22 193.84.116.0/23 193.84.160.0/20 193.84.192.0/19 193.84.192.0/20 193.84.208.0/20 193.84.32.0/20 193.84.53.0/24 193.84.55.0/24 193.84.56.0/21 193.84.80.0/22 195.113.0.0/16 195.178.64.0/19 78.128.128.0/17"
CESNET2_IPV6="2001:718::/32"

TESTNET=$(seq 1 100 | xargs -I{} printf "10.%d.0.0/16 " {})

sh bin/server_command.sh scheduler enumips ${CESNET2_IPV4} | sh bin/server_command.sh scheduler task_add 1 --file - --name "cesnet2_ipv4"
sh bin/server_command.sh scheduler enumips ${TESTNET} | sh bin/server_command.sh scheduler task_add 1 --file - --name "testnet"
