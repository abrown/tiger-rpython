RPYTHON=3rd/pypy/rpython/bin/rpython
VERSION=0.1
IMAGE=dynsem:${VERSION}
LOG=e2-$(shell date +%s).log

# define FAST=1 to avoid the long-compiling JIT option
ifeq (${FAST}, )
JIT_OPT:=jit
else
JIT_OPT:=3
endif

# setup proxy for Docker
ifeq (${http_proxy}, )
PROXY:=
else
PROXY:=--build-arg http_proxy=${http_proxy} --build-arg https_proxy=${https_proxy}
endif

all: test

3rd:
	git submodule update --init --recursive
.PHONY: 3rd

test:
	python -m unittest discover -s src/meta/test -p "*.py" -t .

bin/e2: src/main/e2.py $(shell find src/meta/*.py)
	mkdir -p bin
	PYTHONPATH=. python ${RPYTHON} --log --opt=${JIT_OPT} --output=$@ $<

bin/while: src/main/while.py $(shell find src/meta/*.py) clean-pyc
	mkdir -p bin
	PYTHONPATH=. python ${RPYTHON} --log --opt=${JIT_OPT} --output=$@ $<

bin/sumprimes: src/main/sumprimes.c
	gcc -O0 $< -o $@

run: bin/e2
	PYPYLOG=jit:${LOG} time $< src/main/sumprimes.e2

run-pypy: src/main/sumprimes.py
	PYPYLOG=jit:${LOG} time pypy $<

run-c: bin/sumprimes
	time bin/sumprimes

run-while: bin/e2
	PYPYLOG=jit:${LOG} time $< src/main/while.e2

show-last-log:
	less -N $(shell ls e2-*.log | tail -n 1)

# e.g. `make extract-last-log PATTERN=jit-log-opt-loop`
extract-last-log:
	cat $(shell ls e2-*.log | tail -n 1) | node src/util/extract-log-section.js ${PATTERN}

disassemble: e2.log
	PYTHONPATH=3rd/pypy 3rd/pypy/rpython/jit/backend/tool/viewcode.py $<
	# note: his requires `dot` from graphviz (e.g. dnf install graphviz) and pygame (e.g. pip install pygame)

docker: Dockerfile $(shell find src/meta/*.py)
	docker build ${PROXY} --tag ${IMAGE} .

docker-run: docker
	docker run -it --rm ${IMAGE}

sync:
ifndef to
	$(error 'to' is undefined, e.g. make sync to=user@host:~/path/to/code)
endif
	rsync -Cra --out-format='[%t]--%n' --exclude="3rd" --exclude=".idea" --exclude=".git" --exclude="bin" --exclude="*.pyc" . ${to}
.PHONY: sync

clean: clean-pyc
	rm -f *.log
	rm -rf bin
	docker rmi -f ${IMAGE}
PHONY: clean

clean-pyc:
	rm -f $(shell find src/**/*.pyc)
PHONY: clean-pyc
