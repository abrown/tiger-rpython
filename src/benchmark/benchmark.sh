#!/usr/bin/env bash

TIGER_PROGRAM=$1

mkdir -p var
export PYTHONPATH=.
export PYPYLOG=jit:var/$(basename $1).log

function run() {
    eval "$((/usr/bin/time $1 $2) 2> >(STDERR=$(cat); typeset -p STDERR) > >(STDOUT=$(cat); typeset -p STDOUT))"
    CODE=$?

    echo "$1 $TIGER_PROGRAM"
	echo -e "\tTime: $(echo ${STDERR} | tr -d '\n')"
    echo -e "\tCode: ${CODE}"
    echo -e "\tValue: ${STDOUT}\n"
}

run "python src/main/tiger_interpreter.py" ${TIGER_PROGRAM}
run "bin/tiger-interpreter-no-jit" ${TIGER_PROGRAM}
run "bin/tiger-interpreter" ${TIGER_PROGRAM}
