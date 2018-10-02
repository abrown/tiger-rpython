from src.ast import Exp, Sequence, FunctionDeclaration, FunctionCall, Let, BinaryOperation, LValue, Program, \
    VariableDeclaration


def transform_lvalues(exp):
    """
    :param exp: the root expression of an AST
    :return: nothing, but alter each LValue in the AST to contain a path to its declaration
    """
    assert isinstance(exp, Exp)

    transformer = LValueTransformer()
    for node in DepthFirstAstIterator(exp):
        transformer.transform(node)


class ScopeError(Exception):
    """
    Raised if there is a scoping issue, e.g. an LValue is never declared in any parent scope
    """

    def __init__(self, reason):
        self.reason = reason

    def to_string(self):
        return self.reason
        # TODO sub-class from RPythonizedObject?

    def __str__(self):
        return self.to_string()


class ExitScope:
    """
    Used for marking when the depth-first iterator exits a scope
    """

    def __init__(self, expression):
        assert isinstance(expression, Program)
        self.expression = expression


class DepthFirstAstIterator:
    """
    A depth-first iterator of the AST nodes; e.g. for node in DepthFirstAstIterator(root_expression): ...
    """

    def __init__(self, root):
        assert isinstance(root, Exp)
        self.stack = [root]

    def __iter__(self):
        return self

    def next(self):
        if len(self.stack):
            next_expression = self.stack.pop()
            if not isinstance(next_expression, ExitScope):
                self.push_children_of(next_expression)
            return next_expression
        else:
            raise StopIteration()

    def push_children_of(self, expression):
        if isinstance(expression, Sequence):
            self.push_several(expression.expressions)
        elif isinstance(expression, FunctionDeclaration):
            self.push_one(ExitScope(expression))  # so we know when we are leaving the scope of this expression
            self.push_one(expression.body)
            self.push_several(expression.parameters)
        elif isinstance(expression, FunctionCall):
            self.push_several(expression.arguments)
        elif isinstance(expression, Let):
            self.push_one(ExitScope(expression))  # so we know when we are leaving the scope of this expression
            self.push_several(expression.expressions)
            self.push_several(expression.declarations)
        elif isinstance(expression, BinaryOperation):
            self.push_one(expression.right)
            self.push_one(expression.left)

    def push_one(self, expression):
        assert not isinstance(expression, list)
        self.stack.append(expression)

    def push_several(self, expressions):
        assert isinstance(expressions, list)
        # push the list in reverse order
        for i in range(len(expressions) - 1, -1, -1):
            self.stack.append(expressions[i])


class LValueTransformer:
    """
    Transforms LValues to maintain a path to their declaring scope; this path uses the tuple (hops, index), where hops
    is the number of hops to traverse to the declaring scope and index is the location within that scope. This class
    maintains state--the observed scopes as the AST is traversed in depth-first fashion
    """

    def __init__(self):
        self.scopes = []

    def transform(self, node):
        if isinstance(node, Let):
            names = []
            i = 0
            for i in range(len(node.declarations)):
                declaration = node.declarations[i]
                declaration.index = i
                names.append(declaration.name)
            self.scopes.append(names)
        elif isinstance(node, FunctionDeclaration):
            names = [parameter.name for parameter in node.parameters]
            names.insert(0, node.name)
            self.scopes.append(names)
        elif isinstance(node, LValue):
            node.level, node.index = self.find(node.name)
        elif isinstance(node, FunctionCall):
            node.level, node.index = self.find(node.name)
        elif isinstance(node, ExitScope):
            self.scopes.pop()

    def find(self, name):
        for level in range(len(self.scopes)):
            scope = self.scopes[len(self.scopes) - (level + 1)]
            for index in range(len(scope)):
                if scope[index] == name:
                    return level, index
        raise ScopeError('Unable to find the used name %s in the enclosing scopes' % name)
