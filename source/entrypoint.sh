#!/bin/sh

set -e 

trap "trap - SIGTERM && kill -- $$" SIGINT SIGTERM EXIT SIGHUP

python3 ./update-record.py &
wait