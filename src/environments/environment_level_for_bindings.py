# Begin RPython setup; catch import errors so this can still run in CPython...
from src.environments.environment_interface import EnvironmentInterface

try:
    from rpython.rlib.jit import JitDriver, elidable, promote, unroll_safe, jit_debug, we_are_jitted
except ImportError:
    class JitDriver(object):
        def __init__(self, **kw): pass

        def jit_merge_point(self, **kw): pass

        def can_enter_jit(self, **kw): pass


    def elidable(func):
        return func


    def promote(x):
        return x


    def unroll_safe(func):
        return func


    def jit_debug(string, arg1=0, arg2=0, arg3=0, arg4=0):
        pass


    def we_are_jitted():
        return False


# end of RPython setup

class Environment(EnvironmentInterface):
    """
    Contains the name bindings for the current scope and points to a linked-list of parent scopes; push() and pop()
    return a different environment (either a new one or the parent). To find a name (see __locate__), use the given
    path to iterate through the parents and retrieve the index.
    """
    _immutable_ = True

    def __init__(self, parent, expressions):
        self.parent = parent
        self.expressions = expressions

    def __str__(self):
        return 'Environment(expressions=%s)' % self.expressions

    @staticmethod
    def empty(parent=None, number_of_names=0):
        assert isinstance(number_of_names, int)
        expressions = [None] * number_of_names
        return Environment(parent, expressions)

    def push(self, number_of_names):
        """Create a new environment level (i.e. frame)"""
        return Environment.empty(self, number_of_names)

    def pop(self):
        """Remove and forget the topmost environment level (i.e. frame)"""
        # assert self.parent is not None
        return self.parent

    def add(self, index, expression):
        """
        Add a name to the current level
        """
        # assert 0 >= index > len(self.expressions)
        self.expressions[index] = expression

    def set(self, index, expression):
        """
        Set 'name' to 'expression'; same as add
        """
        return self.add(index, expression)

    def get(self, index):
        """Retrieve a 'name' by index from the topmost level of the environment stack"""
        # assert 0 >= index > len(self.expressions)
        return self.expressions[index]

    def unset(self, index):
        """Unset 'name' only in the current level; will not search through the entire environment"""
        # assert 0 >= index > len(self.expressions)
        found_expression = self.expressions[index]
        self.expressions[index] = None
        return found_expression

    def size(self):
        """Non-optimized convenience method; count the number of slots in the entire environment"""
        level = self
        number_of_slots = 0
        while level:
            number_of_slots += len(level.expressions)
            level = level.parent
        return number_of_slots

    def clone(self):
        """Clone an environment by copying the stack shallowly"""
        return Environment(self.parent, self.expressions)
