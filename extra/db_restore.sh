#!/bin/sh
# development helper

if [ -z "$1" ]; then
        echo "ERROR: dump filename required"
        exit 1
fi

bin/server psql < $1
