class EnvironmentInterface:
    """
    Un-pythonic attempt to define the interface for environments (i.e. scopes)
    """

    def push(self, number_of_names):
        """
        Create a new environment level (i.e. frame)
        """
        raise NotImplementedError()

    def pop(self):
        """
        Remove and forget the topmost environment level (i.e. frame)
        """
        raise NotImplementedError()

    def add(self, name, expression, level):
        """
        Add a name to the current level
        """
        raise NotImplementedError()

    def get(self, name, level=None):
        """
        Retrieve 'name' from the environment stack by searching through all levels
        """
        raise NotImplementedError()

    def set(self, name, expression, level=None):
        """
        Set 'name' to 'expression'; if it exists in a prior level, modify it there; otherwise, add it to the current
        level
        """
        raise NotImplementedError()

    def unset(self, name, level=None):
        """
        Unset 'name' only in the current level; will not search through the entire environment
        """
        raise NotImplementedError()

    def size(self, level=None):
        """
        Non-optimized convenience method; count the number of unique names in the entire environment
        """
        raise NotImplementedError()

    def clone(self):
        """Clone an environment by copying the stack (note that the levels will only be copied shallowly so fix() may
        be necessary so the levels are immune to updates from other sources)"""
        raise NotImplementedError()
