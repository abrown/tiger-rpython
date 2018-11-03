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

    def __init__(self, parent):
        self.parent = parent
        self.bindings = {}  # map of names to indices
        self.expressions = []  # indexed expressions

    def __str__(self):
        return '%s => %s' % (self.bindings, self.expressions)


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
        self.local_variables = local_variables or EnvironmentLevel(None)
        self.local_types = local_types or EnvironmentLevel(None)

    @staticmethod
    def empty(parent=None, number_of_names=0):
        return Environment()

    def push(self, number_of_names):
        """Create a new environment level (i.e. frame)"""
        self.local_variables = EnvironmentLevel(self.local_variables)
        self.local_types = EnvironmentLevel(self.local_types)
        return self

    def pop(self):
        """Remove and forget the topmost environment level (i.e. frame)"""
        assert self.local_variables.parent is not None
        self.local_variables = self.local_variables.parent
        assert self.local_types.parent is not None
        self.local_types = self.local_types.parent
        return self

    def add(self, name, expression, level):
        """
        Add a name to the current level
        """
        assert isinstance(level, EnvironmentLevel)
        index = len(level.expressions)
        level.bindings[name] = index
        level.expressions.append(expression)

    def set(self, name, expression, level=None):
        """
        Set 'name' to 'expression'; if it exists in a prior level, modify it there; otherwise, add it to the current
        level
        """
        level = level or self.local_variables
        assert isinstance(level, EnvironmentLevel)

        found_level, index = self.__locate__(name, level)
        if not found_level:
            # location not found, add it to the current level
            self.add(name, expression, level)
        else:
            # location found, modify it
            found_level.expressions[index] = expression

    def set_type(self, name, expression):
        self.set(name, expression, self.local_types)

    def set_current_level(self, name, expression, level=None):
        """Set 'name' to 'expression' only in the current level; if it exists, modify it; otherwise, add it"""
        level = level or self.local_variables
        assert isinstance(level, EnvironmentLevel)

        if name in level.bindings:
            # if it exists in the current level, overwrite it
            index = level.bindings[name]
            level.expressions[index] = expression
        else:
            # if not, add it
            self.add(name, expression, level)

    def set_type_current_level(self, name, expression):
        self.set_current_level(name, expression, self.local_types)

    def get(self, name, level=None):
        """Retrieve 'name' from the environment stack by searching through all levels"""
        level = level or self.local_variables
        assert isinstance(level, EnvironmentLevel)

        level, index = self.__locate__(name, level)
        if not level or index < 0:
            return None  # TODO throw?
        else:
            return level.expressions[index]

    def get_type(self, name):
        return self.get(name, self.local_types)

    def unset(self, name, level=None):
        """Unset 'name' only in the current level; will not search through the entire environment"""
        level = level or self.local_variables
        assert isinstance(level, EnvironmentLevel)

        # TODO need to remove from the expressions list as well?
        return level.bindings.pop(name, None)

    def size(self, level=None):
        """Non-optimized convenience method; count the number of unique names in the entire environment"""
        level = level or self.local_variables
        names = {}
        while level:
            for name in level.bindings:
                names[name] = 1
            level = level.parent
        return len(names)

    def clone(self):
        """Clone an environment by copying the stack (note that the levels will only be copied shallowly so fix() may
        be necessary so the levels are immune to updates from other sources)"""
        return Environment(self.local_variables, self.local_types)

    @elidable
    def __locate__(self, name, level):
        assert isinstance(name, str)
        assert isinstance(level, EnvironmentLevel)
        while level:
            if name in level.bindings:
                return level, level.bindings[name]
            else:
                level = level.parent
        return None, -1

    def __str__(self):
        return 'Environment(var_stack=%s, type_stack=%s)' % (self.local_variables, self.local_types)
