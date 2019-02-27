#!/bin/sh
set -e

sh tests/server.sh
sh tests/agent.sh
