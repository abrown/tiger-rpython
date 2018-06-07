VARIABLE = 0
FUNCTION = 1
TYPE = 2


class EnvironmentLevel:
    def __init__(self):
        self.bindings = {}  # map of names to indices
        self.expressions = []  # indexed expressions

    def __str__(self):
        return '%s => %s' % (self.bindings, self.expressions)

class Environment:
    """
    Holds a stack of EnvironmentLevels and a level index to the current one; push() and pop() modify this stack and index.
    Each level contains a dictionary of names to expression index (diff. from level index) and a list of indexed expressions.
    To find a name (see __locate__), inspect each dictionary at each level until the name is found and return the level and its expression index
    """

    def __init__(self, level=0, stack=None):
        self.level = level
        self.stack = stack or [EnvironmentLevel()]

    def push(self):
        """Create a new environment level (i.e. frame)"""
        self.stack.append(EnvironmentLevel())
        self.level += 1

    def pop(self):
        """Remove and forget the topmost environment level (i.e. frame)"""
        self.stack.pop()
        self.level -= 1
        assert self.level >= 0

    def set(self, name, expression):
        """Set 'name' to 'expression'; if it exists in a prior level, modify it there; otherwise, add it to the current
        level"""
        level, index = self.__locate__(name)
        if not level:
            # location not found, add it to the current level
            level = self.stack[self.level]
            index = len(level.expressions)
            level.bindings[name] = index
            level.expressions.append(expression)
        else:
            # location found, modify it
            level.expressions[index] = expression

    def set_current_level(self, name, expression):
        """Set 'name' to 'expression' only in the current level; if it exists, modify it; otherwise, add it"""
        level = self.stack[self.level]
        if name in level.bindings:
            # if it exists in the current level, overwrite it
            index = level.bindings[name]
            level.expressions[index] = expression
        else:
            # if not, add it
            index = len(level.expressions)
            level.bindings[name] = index
            level.expressions.append(expression)

    def get(self, name):
        """Retrieve 'name' from the environment stack by searching through all levels"""
        level, index = self.__locate__(name)
        if not level or index < 0:
            return None  # TODO throw?
        else:
            return level.expressions[index]

    def unset(self, name):
        """Unset 'name' only in the current level; will not search through the entire environment"""
        level = self.stack[self.level]
        return level.bindings.pop(name, None)

    def size(self):
        """Non-optimized convenience method; count the number of unique names in the entire environment"""
        names = {}
        for level in self.stack:
            for name in level.bindings:
                names[name] = 1
        return len(names)

    def clone(self):
        """Clone an environment by copying the stack (note that the levels will only be copied shallowly so fix() may
        be necessary so the levels are immune to updates from other sources)"""
        return Environment(self.level, list(self.stack))

    def fix(self):
        """Collapse all of the levels into one to fix the current global display; this has the theoretical benefit of
        making clone() faster since only a 1-item list is copied. In other words, using fix() assumes that a function
        will be declared once (fixed) and called many times (clone)"""
        new_level = EnvironmentLevel()
        for level in self.stack:
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
        return Environment(0, [new_level])

    # TODO make elidable only if we can guarantee that push/pop have not changed
    def __locate__(self, name):
        expression_index = -1
        level_index = self.level
        level = None
        while expression_index < 0 <= level_index:
            level = self.stack[level_index]
            if name in level.bindings:
                expression_index = level.bindings[name]
            else:
                level_index -= 1
        return level if level_index >= 0 else None, expression_index

    def __str__(self):
        return 'Environment(level=%d, stack=[%s])' % (self.level, ', '.join(str(l) for l in self.stack))