from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.rtyper.llinterp import LLInterpreter
from rpython.translator.interactive import Translation

"""
This file describes different ways of interpreting RPython code using the support libraries in PyPy
"""


def interpret_in_python(function, arguments):
    """
    Interpret using the currently-running Python interpreter
    :param function: the RPython function to interpret
    :param arguments: a list of the arguments passed to 'function'
    :return: the interpreted result
    """
    assert callable(function)
    assert isinstance(arguments, list)
    return function(*arguments)


def interpret_as_jitcode(function, arguments):
    """
    Convert to JIT code and interpret the JIT code in three different ways (see
    rpython/jit/metainterp/test/support.py:268): _run_with_blackhole, _run_with_pyjitpl, _run_with_machine_code
    :param function: the RPython function to interpret
    :param arguments: a list of the arguments passed to 'function'
    :return: the interpreted result
    """
    """"""
    assert callable(function)
    assert isinstance(arguments, list)
    jit = LLJitMixin()
    return jit.interp_operations(function, arguments)


def meta_interpret(function, arguments):
    """
    Meta-interpret the function with ll_meta_interp to produce traces (not sure how this is different than pyjitpl above). NOTE: remember
    that printing out jitcodes is only available when 'verbose = True' is set in
    rpython/jit/metainterp/warmspot.py:277
    :param function: the RPython function to interpret
    :param arguments: a list of the arguments passed to 'function'
    :return: the interpreted result
    """
    assert callable(function)
    assert isinstance(arguments, list)
    assert not any([not isinstance(a, int) for a in arguments]), "Remember not to pass in objects to meta_interpret"
    jit = LLJitMixin()
    return jit.meta_interp(function, arguments, listops=True, inline=True)


def interpret_from_graph(self, rtyper, graph):
    """
    :param rtyper: see translation.driver.translator.rtyper
    :param graph: see translation.driver.translator.graphs[0]
    :return: the interpreted result
    """
    interpreter = LLInterpreter(rtyper)
    return interpreter.eval_graph(graph)  # interpret all translated operations


def translate_to_graph(function, arguments):
    """
    Translate a function to basic blocks and visualize these blocks (see requirements.txt for necessary pip
    packages); use this mechanism in conjunction with interpret_from_graph
    :param function: the RPython function to interpret
    :param arguments: a list of the arguments passed to 'function'
    :return: the translator RTyper and the basic block graph for the function passed
    """
    assert callable(function)
    assert isinstance(arguments, list)
    translation = Translation(function, arguments)
    translation.annotate()
    translation.rtype()
    translation.backendopt()
    translation.view()
    return translation.driver.translator.rtyper, translation.driver.translator.graphs[0]
