#!/bin/sh
set -e

for all in $(find tests/agent -type f -name 'test_*sh'); do 
	echo "INFO: run test $all"
	sh $all
done
