class RPythonizedObject:
    def to_string(self):
        return self.__class__.__name__  # by default just print the class name

    def __str__(self):
        return self.to_string()

    def __repr__(self):
        return self.to_string()

    def equals(self, other):
        return isinstance(other, self.__class__)
        # TODO inline

    def __eq__(self, other):
        return self.equals(other)
