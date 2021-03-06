# tiger-rpython

This project contains an AST-based interpreter for the Tiger language using the RPython meta-tracing framework for 
self-optimizing at runtime. Tiger is a small, imperative language designed by Dr. Andrew Appel in his _Modern
Compiler Implementation_ textbooks. This implementation follows his textbook closely, much like Hirzel and Rose's 
[_Tiger Language Specification_](https://cs.nyu.edu/courses/fall13/CSCI-GA.2130-001/tiger-spec.pdf) and unlike the class
extensions of EPITA's [_Tiger Compiler Reference Manual_](https://www.lrde.epita.fr/~tiger/tiger.html). RPython is a
toolchain for lowering Python to C and JIT-compiling traces of repeated code at runtime; Benjamin Peterson describes
RPython's architecture and how it is employed in the PyPy project in [_The Architecture of Open Source Applications: 
PyPy_](http://www.aosabook.org/en/pypy.html).


### Build

Pre-requisites: _git_, _make_, _Python 2.7_.

```bash
# clone the PyPy repository and verify that the RPython translator works (this project used revision 33f417d9c3f73dadb61346aa1b2579a1bf947ee9 but any recent version should do)
git clone https://github.com/mozillazg/pypy
python pypy/rpython/bin/rpython --help

# clone the tiger-rpython repository (note: currently the Makefile expects the pypy directory to be in the parent directory)
git clone https://github.com/abrown/tiger-rpython
cd tiger-rpython

# create a Python virtual environment with necessary libraries
make venv
source venv/bin/activate

# build 'tiger-parser' and 'tiger-interpreter' under the 'bin' directory
make binaries
```


### Use

For ease of testing, the project builds two RPython-translated binaries in the `bin` directory:

 - `tiger-parser [program.tig]` parses a Tiger program and prints its AST; it returns code `40` when it cannot find the
  Tiger program file, code `42` if the Tiger program is unparseable, and `0` otherwise
 - `tiger-interpreter [program.tig]` parses a Tiger program, evaluates it to a value, and prints this value (if the
 program returns a value at all); it returns similar codes to `tiger-parser`



### Test

This project contains several distinct test sets that are used to verify different parts of the interpreter; the files
live in `src/test` and include:

 - Python unit tests: Python `unittest` code that tests specific functions of the Tiger interpreter 
 (e.g. `src/test/tokenizing.py`)
 - `appel-tests`: These Tiger programs (some of which are purposely incorrect) are borrowed from Dr. Andrew Appel's 
 _Modern Compiler Implementation_ book; see published files at 
 [the book's site](https://www.cs.princeton.edu/~appel/modern/testcases/); currently they are used for verifying 
 correct parsing, not evaluation
 - `expr-tests`: These Tiger programs are simple expressions; the expression is interpreted to a value and compared 
 against values a corresponding `[test name].out.bak` file
 - `print-tests`: These Tiger programs are complex expressions that `print()` values during their evaluation; the printed
 values are collected and compared a corresponding `[test name].out.bak` file

When _unit tests_ run, a Python interpreter executes `unittest` cases that include 1) the `*.py` files in `src/test`, 2)
the Python-interpreted evaluation of the `expr-tests` expressions, and 3) the Python-interpreted evaluation of the 
`print-tests` programs; to run them, execute:

```bash
make test
```
When _integration tests_ run, the `tiger-parser` and `tiger-interpreter` binaries are built by RPython and used for 1)
comparing the Python-interpreted parsing against the RPython-compiled parsing of the `appel-tests` (i.e. the parsed
AST is printed by both `python src/main/tiger-parser.py` and `bin/tiger-parser` and compared to ensure no discrepancies)
and 2) verifying that the RPython-compiled `tiger-interpreter` correctly evaluates the `print-tests` programs. To run 
these, execute:

```bash
make integration-test
```


### Features

This list describes which Tiger language features implemented (and which not):

 - Valid Tiger programs are parsed correctly; no errors are raised, however, for typing issues (e.g. `var i : int = "a string"`)
 - Except for `print(s : string)`, the standard library functions (e.g. `concat`, `exit`, `substring`) are not implemented
 - Control flow expressions such as sequences, `if-then-else`, `for`, and `while` evaluate as expected, including `break` for loops
 - Function declarations (including nesting) and function calls (left-to-right parameter evaluation)
 - Declare and assign to variables with `lets`, including nested `lets`
 - Allows creation of arrays and records and referencing them with lvalues
 - No type-checking of values (yet)
 


### References

Some helpful documents explaining RPython:

 - Summary of the RPython architecture (e.g. the translation toolchain `flowspace` -> `annotator` -> `rtyper` and the 
 meta-interpreter in `jit`): http://doc.pypy.org/en/latest/architecture.html
 - JIT compiler architecture, including off-line partial evaluation principles (translation time vs compile time vs 
 runtime), distinction of green vs red (green are known at compile time, red are not known until runtime), and promotion
 (stop compilation until the runtime reaches this point): https://bitbucket.org/pypy/extradoc/raw/tip/eu-report/D08.2_JIT_Compiler_Architecture-2007-05-01.pdf
 - In-depth PyPy description, including flow space, annotation model: https://bitbucket.org/pypy/extradoc/raw/tip/eu-report/D05.1_Publish_on_translating_a_very-high-level_description.pdf
 - Using RPython interactively (e.g. displaying the flow graph): http://rpython.readthedocs.io/en/latest/getting-started.html
