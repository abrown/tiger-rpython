RPYTHON=3rd/pypy/rpython/bin/rpython
VERSION=0.1

all: test

test:
	python3 -m unittest discover -s src/test -p "*.py" -t .

clean: clean-pyc
	rm -f *.log
	rm -rf bin
PHONY: clean

clean-pyc:
	rm -f $(shell find src/**/*.pyc)
PHONY: clean-pyc
