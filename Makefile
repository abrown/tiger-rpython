RPYTHON=../pypy/rpython/bin/rpython
VERSION=0.1

all: test

test:
	python3 -m unittest discover -s src/test -p "*.py" -t .

parser: src/main.py $(shell find src/*.py)
	mkdir -p bin
	PYTHONPATH=. python ${RPYTHON} --log --opt=jit --output=$@ $<

clean: clean-pyc
	rm -f *.log
	rm -rf bin
PHONY: clean

clean-pyc:
	rm -f $(shell find src/**/*.pyc)
PHONY: clean-pyc
