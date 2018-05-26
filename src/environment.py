VARIABLE=0
FUNCTION=1
TYPE=2

class Environment:
    def __init__(self):
        self.bindings = {}
        self.old = []

    def push(self):
        self.old.insert(0, self.bindings)
        self.bindings = self.__copy__(self.bindings)

    def __copy__(self, bindings):
        new_bindings = {}
        for name in bindings:
            new_bindings[name] = bindings[name]
        return new_bindings

    def pop(self):
        self.bindings = self.old.pop(0)

    def set(self, name, expression):
        old = self.bindings[name] if name in self.bindings else None
        self.bindings[name] = expression
        return old

    def get(self, name):
        return self.bindings[name] if name in self.bindings else None

    def unset(self, name):
        old = self.bindings[name] if name in self.bindings else None
        self.bindings[name] = None
        return old
