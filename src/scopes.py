from src.ast import Exp, Sequence, FunctionDeclaration, FunctionCall, Let, BinaryOperation, LValue, Program, \
    TypeDeclaration, ArrayCreation, VariableDeclaration, For, While, If, Assign, \
    RecordCreation, ArrayLValue, RecordLValue, TypeId

NATIVE_FUNCTION_NAMES = [
    'print'
]

NATIVE_TYPES = [
    'int'
]


def transform_lvalues(exp, existing_names=None, existing_types=None):
    """
    :param exp: the root expression of an AST
    :return: nothing, but alter each LValue in the AST to contain a path to its declaration
    """
    assert isinstance(exp, Exp)

    transformer = LValueTransformer(existing_names or NATIVE_FUNCTION_NAMES, existing_types or NATIVE_TYPES)
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
        elif isinstance(expression, TypeDeclaration):
            self.push_one(expression.type)
        elif isinstance(expression, VariableDeclaration):
            self.push_one(expression.exp)
            if expression.type:
                self.push_one(expression.type)
        elif isinstance(expression, ArrayCreation):
            self.push_one(expression.initial_value_expression)
            self.push_one(expression.length_expression)
        elif isinstance(expression, RecordCreation):
            self.push_several(expression.fields.values())
            self.push_one(expression.type_id)
        elif isinstance(expression, For):
            self.push_one(expression.while_expression)  # this should be body but For() has been converted to a While
        elif isinstance(expression, While):
            self.push_one(expression.body)
            self.push_one(expression.condition)
        elif isinstance(expression, If):
            self.push_one(expression.body_if_false)
            self.push_one(expression.body_if_true)
            self.push_one(expression.condition)
        elif isinstance(expression, Assign):
            self.push_one(expression.expression)
            self.push_one(expression.lvalue)
        elif isinstance(expression, LValue):
            if expression.next:
                self.push_one(expression.next)
            if isinstance(expression, ArrayLValue):
                self.push_one(expression.exp)

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

    def __init__(self, existing_names=None, existing_types=None):
        self.variable_scopes = [] or [existing_names]
        assert isinstance(self.variable_scopes, list)
        self.type_scopes = [] or [existing_types]
        assert isinstance(self.variable_scopes, list)

    def transform(self, node):
        if isinstance(node, Let):
            variables = []
            types = []

            # TODO need to separate out type declarations and binding declarations
            for i in range(len(node.declarations)):
                declaration = node.declarations[i]
                if isinstance(declaration, TypeDeclaration):
                    declaration.index = len(types)
                    types.append(declaration.name)
                else:
                    declaration.index = len(variables)
                    variables.append(declaration.name)

            self.variable_scopes.append(variables)
            self.type_scopes.append(types)

        elif isinstance(node, FunctionDeclaration):
            names = [parameter.name for parameter in node.parameters]
            names.insert(0, node.name)
            self.variable_scopes.append(names)
            self.type_scopes.append([])
        elif isinstance(node, LValue):
            if isinstance(node, ArrayLValue):
                # if an expression is used to index into the array, it will be transformed as we iterate over the tree
                pass
            elif isinstance(node, RecordLValue):
                # TODO eventually store records as arrays and index into the array here
                pass
            else:
                node.level, node.index = self.find_variable(node.name)
        elif isinstance(node, FunctionCall):
            node.level, node.index = self.find_variable(node.name)
        elif isinstance(node, TypeId):
            node.level, node.index = self.find_type(node.name)
        elif isinstance(node, ExitScope):
            self.variable_scopes.pop()
            self.type_scopes.pop()

    def find_variable(self, name):
        return self.find(name, self.variable_scopes)

    def find_type(self, name):
        return self.find(name, self.type_scopes)

    def find(self, name, scopes):
        for level in range(len(scopes)):
            scope = scopes[len(scopes) - (level + 1)]
            for index in range(len(scope)):
                if scope[index] == name:
                    return level, index
        raise ScopeError('Unable to find the name %s in the enclosing scopes' % name)
