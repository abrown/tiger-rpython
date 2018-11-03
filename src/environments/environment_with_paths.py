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

class EnvironmentLevel:
    """
    Contains the name bindings at a given level
    """
    _immutable_ = True

    def __init__(self, parent, number_of_names):
        assert isinstance(number_of_names, int)
        self.parent = parent
        self.expressions = [None] * number_of_names  # indexed expressions

    def __str__(self):
        return '%s' % self.expressions


class Environment(EnvironmentInterface):
    """
    Holds a linked-list of EnvironmentLevels and points to the last one; push() and pop() modify this stack and index.
    Each level contains a dictionary of names to expression index (diff. from level index) and a list of indexed \
    expressions. To find a name (see __locate__), inspect each dictionary at each level until the name is found and
    return the level and its expression index
    """
    _immutable_ = True

    # TODO specialize get/set/etc. on stack passed
    def __init__(self, local_variables=None, local_types=None):
        self.local_variables = local_variables or EnvironmentLevel(None, 0)  # TODO root level
        self.local_types = local_types or EnvironmentLevel(None, 0)  # TODO root level

    def push(self, number_of_names):
        """Create a new environment level (i.e. frame)"""
        self.local_variables = EnvironmentLevel(self.local_variables, number_of_names)  # TODO should be (total - types)
        self.local_types = EnvironmentLevel(self.local_types, number_of_names)  # TODO should be (total - variables)

    def pop(self):
        """Remove and forget the topmost environment level (i.e. frame)"""
        assert self.local_variables.parent is not None
        self.local_variables = self.local_variables.parent
        assert self.local_types.parent is not None
        self.local_types = self.local_types.parent

    def add(self, index, expression, level):
        """
        Add a name to the current level
        """
        assert isinstance(level, EnvironmentLevel)
        assert 0 >= index > len(level.expressions)
        level.expressions[index] = expression

    def set(self, path, expression, level=None):
        """
        Set 'name' to 'expression'; if it exists in a prior level, modify it there; otherwise, add it to the current
        level
        """
        level = level or self.local_variables
        assert isinstance(level, EnvironmentLevel)

        found_level, found_index = self.__locate__(path, level)
        # location found, modify it (otherwise locate will raise)
        found_level.expressions[found_index] = expression

    def get(self, path, level=None):
        """Retrieve 'name' from the environment stack by searching through all levels"""
        level = level or self.local_variables
        assert isinstance(level, EnvironmentLevel)

        found_level, found_index = self.__locate__(path, level)
        return found_level.expressions[found_index]

    def unset(self, path, level=None):
        """Unset 'name' only in the current level; will not search through the entire environment"""
        level = level or self.local_variables
        assert isinstance(level, EnvironmentLevel)

        found_level, found_index = self.__locate__(path, level)
        found_expression = found_level.expressions[found_index]
        found_level.expressions[found_index] = None
        return found_expression

    def size(self, level=None):
        """Non-optimized convenience method; count the number of slots in the entire environment"""
        level = level or self.local_variables
        number_of_slots = 0
        while level:
            number_of_slots += len(level.expressions)
            level = level.parent
        return number_of_slots

    def clone(self):
        """Clone an environment by copying the stack (note that the levels will only be copied shallowly so fix() may
        be necessary so the levels are immune to updates from other sources)"""
        return Environment(self.local_variables, self.local_types)

    @unroll_safe
    def __locate__(self, path, level):
        assert isinstance(level, EnvironmentLevel)

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

    def __str__(self):
        return 'Environment(var_stack=%s, type_stack=%s)' % (self.local_variables, self.local_types)
