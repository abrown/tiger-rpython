#!/bin/bash

export PYTHONPATH=.

rpython_value=$(bin/tiger-interpreter $1 2>&1)
rpython_code=$?

expected_value=$(cat "${1%.tig}.out.bak")

if [ ${DEBUG} ]; then
	echo -e "\tRPython (code: $rpython_code): $rpython_value"
    echo -e "\tExpected:                     $expected_value"
fi

if [ ${rpython_code} != 0 ]; then
	echo "Failed: non-zero error code for $1, rpython == ${rpython_code}"
	echo -e "\tRPython: $rpython_value"
	exit 1
elif [ "${rpython_value}" != "${expected_value}" ]; then
    echo "Failed: different results for $1"
	echo -e "\tExpected:  $expected_value"
	echo -e "\tRPython: $rpython_value"
	exit 2
else
	echo "Success: $1"
	exit 0
fi
