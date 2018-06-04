RPYTHON=../pypy/rpython/bin/rpython
VERSION=0.1

all: test

test:
	python3 -m unittest discover -s src/test -p "*.py" -t .

integration-test: bin/tiger-parser
	$(foreach test, $(shell find 3rd/appel-modern/*.tig), ./integration-test.sh $(test);)

bin/tiger-parser: src/main/tiger-parser.py $(shell find src/*.py)
	mkdir -p bin
	PYTHONPATH=. python ${RPYTHON} --log --opt=3 --output=$@ $<

bin/tiger-interpreter: src/main/tiger-interpreter.py $(shell find src/*.py) bin
	PYTHONPATH=3rd/pypy:. python ${RPYTHON} --log --opt=jit --output=$@ $<

bin:
	mkdir -p bin

clean: clean-pyc
	rm -f *.log
	rm -rf bin
PHONY: clean

clean-pyc:
	rm -f $(shell find src/**/*.pyc)
PHONY: clean-pyc
