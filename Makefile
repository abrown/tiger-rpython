RPYTHON=../pypy/rpython/bin/rpython
VERSION=0.1

all: test

test:
	python3 -m unittest discover -s src/test -p "*.py" -t .

integration-test: integration-test-parsing integration-test-evaluating

integration-test-parsing: bin/tiger-parser
	$(foreach test, $(shell find src/test/appel-tests/*.tig), ./src/integration-test/python-vs-rpython-parsing.sh $(test);)

integration-test-evaluating: bin/tiger-interpreter
	$(foreach test, $(shell find src/test/print-tests/*.tig), ./src/integration-test/rpython-evaluating.sh $(test);)



binaries: bin/tiger-parser bin/tiger-interpreter bin/tiger-interpreter-no-jit

bin/tiger-parser: src/main/tiger-parser.py src/main/util.py $(shell find src/*.py)
	mkdir -p bin
	PYTHONPATH=. python ${RPYTHON} --log --opt=3 --output=$@ $<

bin/tiger-interpreter: src/main/tiger-interpreter.py src/main/util.py $(shell find src/*.py)
	mkdir -p bin
	PYTHONPATH=. python ${RPYTHON} --log --opt=jit --output=$@ $<

bin/tiger-interpreter-no-jit: src/main/tiger-interpreter.py src/main/util.py $(shell find src/*.py)
	mkdir -p bin
	PYTHONPATH=. python ${RPYTHON} --log --opt=3 --output=$@ $<


benchmarks: binaries
	$(foreach program, $(shell find src/benchmark/*.tig), ./src/benchmark/benchmark.sh $(program);)


clean: clean-pyc
	rm -f *.log
	rm -rf bin
PHONY: clean

clean-pyc:
	rm -f $(shell find src/**/*.pyc)
PHONY: clean-pyc
