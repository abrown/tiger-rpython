class Environment:
    def __init__(self):
        self.bindings = {}

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
