# Begin RPython setup; catch import errors so this can still run in CPython...
from src.environments.environment_interface import EnvironmentInterface

try:
    from rpython.rlib.jit import JitDriver, elidable, hint, promote, unroll_safe, jit_debug, we_are_jitted
except ImportError:
    class JitDriver(object):
        def __init__(self, **kw): pass

        def jit_merge_point(self, **kw): pass

        def can_enter_jit(self, **kw): pass


    def elidable(func):
        return func


    def hint(x, **kwds):
        return x


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

    # _virtualizable_ = ['parent', 'expressions[*]', 'types[*]']

    def __init__(self, parent, expressions, types):
        self = hint(self, access_directly=True, fresh_virtualizable=True)
        self.parent = parent
        self.expressions = expressions
        self.types = types

    def __str__(self):
        return 'Environment(expressions=%s, types=%s)' % (self.expressions, self.types)

    @staticmethod
    def empty(parent=None, number_of_names=0):
        assert isinstance(number_of_names, int)
        expressions = [None] * number_of_names  # TODO should be (total - types)
        types = [None] * number_of_names  # TODO should be (total - variables)
        return Environment(parent, expressions, types)

    def push(self, number_of_names):
        """Create a new environment level (i.e. frame)"""
        return Environment.empty(self, number_of_names)

    def pop(self):
        """Remove and forget the topmost environment level (i.e. frame)"""
        assert self.parent is not None
        return self.parent

    def add(self, index, expression):
        """
        Add a name to the current level
        """
        assert 0 >= index > len(self.expressions)
        self.expressions[index] = expression

    def set(self, path, expression):
        """
        Set 'name' to 'expression'; if it exists in a prior level, modify it there; otherwise, add it to the current
        level
        """
        found_level, found_index = self.__locate__(path, self)
        # location found, modify it (otherwise locate will raise)
        found_level.expressions[found_index] = expression

    def set_type(self, path, type):
        found_level, found_index = self.__locate__(path, self)
        # location found, modify it (otherwise locate will raise)
        found_level.types[found_index] = type

    def get(self, path):
        """Retrieve 'name' from the environment stack by searching through all levels"""
        found_level, found_index = self.__locate__(path, self)
        return found_level.expressions[found_index]

    def get_type(self, path):
        found_level, found_index = self.__locate__(path, self)
        return found_level.types[found_index]

    def unset(self, path):
        """Unset 'name' only in the current level; will not search through the entire environment"""
        found_level, found_index = self.__locate__(path, self)
        found_expression = found_level.expressions[found_index]
        found_level.expressions[found_index] = None
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
        return self
        #return Environment(self.parent, [e for e in self.expressions], [t for t in self.types])

    @staticmethod
    @unroll_safe
    def __locate__(path, level):
        assert isinstance(level, Environment)

        hops, index = path
        assert isinstance(hops, int)
        assert isinstance(index, int)

        while hops >= 0 and level:
            if hops == 0:
                if not 0 <= index < len(level.expressions):
                    break  # in this case we have not found a valid slot for the path and should throw an error
                return level, index
            hops -= 1
            level = level.parent

        raise EnvironmentError('Expected path (%d, %d) to lead to a valid scope but it did not' % (path[0], index))
