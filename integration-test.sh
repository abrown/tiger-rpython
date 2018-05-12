#!/bin/bash

export PYTHONPATH=.
python_value=$(python src/main.py $1 2>&1)
python_code=$?

rpython_value=$(bin/parser $1 2>&1)
rpython_code=$?

if [ ${DEBUG} ]; then
	echo "${python_code} == ${rpython_code}"
fi

if [ ${python_code} != ${rpython_code} ]; then
	echo "Failed: different error codes for $1, python == ${python_code}, rpython == ${rpython_code}"
	exit 1
else
	echo "Success"
	exit 0
fi
