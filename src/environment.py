# Begin RPython setup; catch import errors so this can still run in CPython...
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


class Cloneable:
    def clone(self):
        return self


class EnvironmentLevel:
    """
    Contains the name bindings at a given level
    """
    _immutable_ = True

    def __init__(self):
        self.bindings = {}  # map of names to indices
        self.expressions = []  # indexed expressions

    def __str__(self):
        return '%s => %s' % (self.bindings, self.expressions)


class Environment(Cloneable):
    """
    Holds a stack of EnvironmentLevels and a level index to the current one; push() and pop() modify this stack and index.
    Each level contains a dictionary of names to expression index (diff. from level index) and a list of indexed expressions.
    To find a name (see __locate__), inspect each dictionary at each level until the name is found and return the level and its expression index
    """
    _immutable_ = True

    # TODO specialize get/set/etc. on stack passed
    def __init__(self, stack=None, type_stack=None):
        self.var_stack = stack or [EnvironmentLevel()]
        self.type_stack = type_stack or [EnvironmentLevel()]

    def push(self):
        """Create a new environment level (i.e. frame)"""
        self.var_stack.append(EnvironmentLevel())
        self.type_stack.append(EnvironmentLevel())

    def pop(self):
        """Remove and forget the topmost environment level (i.e. frame)"""
        assert (len(self.var_stack) > 0)
        self.var_stack.pop()
        assert (len(self.type_stack) > 0)
        self.type_stack.pop()

    def set(self, name, expression, stack=None):
        """
        Set 'name' to 'expression'; if it exists in a prior level, modify it there; otherwise, add it to the current
        level
        """
        stack = stack or self.var_stack
        level, index = self.__locate__(name, stack)
        if not level:
            # location not found, add it to the current level
            level = stack[-1]
            index = len(level.expressions)
            level.bindings[name] = index
            level.expressions.append(expression)
        else:
            # location found, modify it
            level.expressions[index] = expression

    def set_current_level(self, name, expression, stack=None):
        """Set 'name' to 'expression' only in the current level; if it exists, modify it; otherwise, add it"""
        stack = stack or self.var_stack
        level = stack[-1]
        if name in level.bindings:
            # if it exists in the current level, overwrite it
            index = level.bindings[name]
            level.expressions[index] = expression
        else:
            # if not, add it
            index = len(level.expressions)
            level.bindings[name] = index
            level.expressions.append(expression)

    def get(self, name, stack=None):
        """Retrieve 'name' from the environment stack by searching through all levels"""
        stack = stack or self.var_stack
        level, index = self.__locate__(name, stack)
        if not level or index < 0:
            return None  # TODO throw?
        else:
            return level.expressions[index]

    def unset(self, name, stack=None):
        """Unset 'name' only in the current level; will not search through the entire environment"""
        stack = stack or self.var_stack
        level = stack[-1]
        return level.bindings.pop(name, None)

    def size(self):
        """Non-optimized convenience method; count the number of unique names in the entire environment"""
        names = {}
        for level in self.var_stack:
            for name in level.bindings:
                names[name] = 1
        return len(names)

    def clone(self):
        """Clone an environment by copying the stack (note that the levels will only be copied shallowly so fix() may
        be necessary so the levels are immune to updates from other sources)"""
        return Environment(list(self.var_stack), list(self.type_stack))

    def fix(self):
        """Collapse all of the levels into one to fix the current global display; this has the theoretical benefit of
        making clone() faster since only a 1-item list is copied. In other words, using fix() assumes that a function
        will be declared once (fixed) and called many times (clone)"""
        new_var_stack = self.__collapse__(self.var_stack)
        new_type_stack = self.__collapse__(self.type_stack)
        return Environment(new_var_stack, new_type_stack)

    def __collapse__(self, stack):
        """
        Iterate over all levels and record all unique names; later levels will overwrite previous levels' names if they
        are the same name
        """
        new_level = EnvironmentLevel()
        for level in stack:
            for name in level.bindings:
                old_index = level.bindings[name]
                expression = level.expressions[old_index]
                if name in new_level.bindings:
                    # if it exists in the current level, overwrite it
                    new_index = new_level.bindings[name]
                    new_level.expressions[new_index] = expression
                else:
                    # if not, add it
                    new_index = len(new_level.expressions)
                    new_level.bindings[name] = new_index
                    new_level.expressions.append(expression)
        return [new_level]

    # TODO make elidable only if we can guarantee that push/pop have not changed
    @elidable
    def __locate__(self, name, stack):
        expression_index = -1
        level_index = len(stack) - 1
        level = None
        while expression_index < 0 <= level_index:
            level = stack[level_index]
            if name in level.bindings:
                expression_index = level.bindings[name]
            else:
                level_index -= 1
        return level if level_index >= 0 else None, expression_index

    def __str__(self):
        return 'Environment(level=%d, stack=[%s])' % (self.level, ', '.join(str(l) for l in self.var_stack))
