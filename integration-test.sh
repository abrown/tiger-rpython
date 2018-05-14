#!/bin/bash

export PYTHONPATH=.
python_value=$(python src/main.py $1 2>&1)
python_code=$?
#python_hash=$(echo -e ${python_value} | md5sum}

rpython_value=$(bin/parser $1 2>&1)
rpython_code=$?
#rpython_hash=$(echo -e ${rpython_value} | md5sum}

if [ ${DEBUG} ]; then
	echo -e "\tPython (code: $python_code):   $python_value"
    echo -e "\tRPython (code: $rpython_code): $rpython_value"
fi

if [ ${python_code} != ${rpython_code} ]; then
	echo "Failed: different error codes for $1, python == ${python_code}, rpython == ${rpython_code}"
	echo -e "\tPython:  $python_value"
	echo -e "\tRPython: $rpython_value"
	exit 1
elif [ "${python_value}" != "${rpython_value}" ]; then
    echo "Failed: different results for $1"
	echo -e "\tPython:  $python_value"
	echo -e "\tRPython: $rpython_value"
	exit 2
else
	echo "Success: $1"
	exit 0
fi
