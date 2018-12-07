#!/usr/bin/env bash

set -e
PROJECT_DIR=$(realpath $(dirname "${BASH_SOURCE[0]}")/../../..)
PYPY_DIR=$(realpath ${PROJECT_DIR}/../pypy)

for BRANCH in "env-with-dicts" "env-with-paths" "env-embedded-in-ast"
do
  CLONE_DIR=/tmp/tiger-rpython-${BRANCH}
  LOG_PREFIX="\n[${BRANCH}] >"

  echo -e "${LOG_PREFIX} Creating a new instance of the repo:"
  rm -rf ${CLONE_DIR}
  git clone ${PROJECT_DIR} ${CLONE_DIR}

  echo -e "${LOG_PREFIX}  Rebasing environment commit on top:"
  pushd ${CLONE_DIR}
  git checkout $BRANCH
  git rebase master
  #git push --force  # to keep the repository up to date

  echo -e "${LOG_PREFIX}  Now the history is:"
  git log --oneline -n 5

  echo -e "${LOG_PREFIX}  Ensure tests still work:"
  make test

  echo -e "${LOG_PREFIX}  Build the interpreter:"
  mkdir var
  PYPY=${PYPY_DIR} make binaries &> var/build.log

  echo -e "${LOG_PREFIX}  Ensure integration tests still work:"
  make integration-test

  echo -e "${LOG_PREFIX}  Run benchmark:"
  make benchmarks-environment-comparison
  cp var/environment-comparison-${BRANCH}.pkl ${PROJECT_DIR}/var

  popd
done
