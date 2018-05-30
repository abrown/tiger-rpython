VARIABLE = 0
FUNCTION = 1
TYPE = 2


class EnvironmentLevel:
    def __init__(self):
        self.bindings = {}  # map of names to indices
        self.expressions = []  # indexed expressions


class Environment:
    """
    Holds a stack of EnvironmentLevels and a level index to the current one; push() and pop() modify this stack and index.
    Each level contains a dictionary of names to expression index (diff. from level index) and a list of indexed expressions.
    To find a name (see __locate__), inspect each dictionary at each level until the name is found and return the level and its expression index
    """

    def __init__(self):
        self.level = 0
        self.stack = [EnvironmentLevel()]

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
        """Non-optimized onvenience method; count the number of unique names in the entire environment"""
        names = {}
        for level in self.stack:
            for name in level.bindings:
                names[name] = 1
        return len(names)

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
