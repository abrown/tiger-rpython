PYPY=../pypy
RPYTHON=../pypy/rpython/bin/rpython
VERSION=0.1

all: test



test:
	python -m unittest discover -s src/test -p "*.py" -t .

integration-test: integration-test-parsing integration-test-evaluating

integration-test-parsing: bin/tiger-parser
	$(foreach test, $(shell find src/test/appel-tests/*.tig), ./src/integration-test/python-vs-rpython-parsing.sh $(test);)

integration-test-evaluating: bin/tiger-interpreter
	$(foreach test, $(shell find src/test/print-tests/*.tig), ./src/integration-test/rpython-evaluating.sh $(test);)



binaries: bin/tiger-parser bin/tiger-interpreter bin/tiger-interpreter-no-jit

bin/tiger-parser: src/main/tiger_parser.py src/main/util.py $(shell find src/*.py)
	mkdir -p bin
	PYTHONPATH=. python ${RPYTHON} --log --opt=3 --output=$@ $<

bin/tiger-interpreter: src/main/tiger_interpreter.py src/main/util.py $(shell find src/*.py)
	mkdir -p bin
	PYTHONPATH=. python ${RPYTHON} --log --opt=jit --output=$@ $<

bin/tiger-interpreter-no-jit: src/main/tiger_interpreter.py src/main/util.py $(shell find src/*.py)
	mkdir -p bin
	PYTHONPATH=. python ${RPYTHON} --log --opt=3 --output=$@ $<



benchmarks: binaries
	$(foreach program, $(shell find src/benchmark/*.tig), ./src/benchmark/benchmark.sh $(program);)
PHONY: benchmarks

venv:
	python -m virtualenv --python=/usr/bin/python2.7 venv
	source venv/bin/activate && pip install -r requirements.txt
	ln -s $(shell realpath ${PYPY}/rpython) venv/lib/python2.7/site-packages/
	ln -s $(shell realpath ${PYPY}/dotviewer) venv/lib/python2.7/site-packages/
	ln -s $(shell realpath ${PYPY}/py) venv/lib/python2.7/site-packages/
	ln -s $(shell realpath ${PYPY}/_pytest) venv/lib/python2.7/site-packages/
	ln -s $(shell realpath ${PYPY}/pytest.py) venv/lib/python2.7/site-packages/

clean: clean-pyc
	rm -f *.log
	rm -rf bin
PHONY: clean

clean-pyc:
	rm -f $(shell find src/**/*.pyc)
PHONY: clean-pyc
