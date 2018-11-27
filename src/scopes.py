from src.ast import Exp, Sequence, FunctionDeclaration, FunctionCall, Let, BinaryOperation, LValue, Program, \
    TypeDeclaration, ArrayCreation, VariableDeclaration, For, While, If, Assign, \
    RecordCreation, ArrayLValue, RecordLValue, TypeId, Declaration, FunctionParameter, NativeFunctionDeclaration


def transform_lvalues(exp, existing_declarations=None):
    """
    :param exp: the root expression of an AST
    :param existing_declarations: a list of already-available declarations in this scope
    :return: nothing, but alter each LValue in the AST to contain a path to its declaration
    """
    assert isinstance(exp, Program)

    transformer = LValueTransformer(existing_declarations or [])
    for node in DepthFirstAstIterator(exp):
        transformer.transform(node)

    # we must also transform any declarations passed, e.g. in case they contain lvalues internally
    if isinstance(existing_declarations, list):
        for declaration in existing_declarations:
            transform_lvalues(declaration, None)


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


class ExitScope(Exp):
    """
    Used for marking when the depth-first iterator exits a scope
    NOTE: this must subclass expression to satisfy RPython, not for any other reason.
    """
    _immutable_ = True

    def __init__(self, expression):
        assert isinstance(expression, Program)
        self.expression = expression


class DepthFirstAstIterator:
    """
    A depth-first iterator of the AST nodes; e.g. for node in DepthFirstAstIterator(root_expression): ...
    """

    def __init__(self, root):
        assert isinstance(root, Program)
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
            self.push_one(expression.expression)
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

    def __init__(self, existing_declarations=None):
        self.scopes = existing_declarations or []
        assert isinstance(self.scopes, list)

    def transform(self, node):
        if isinstance(node, Let):
            self.scopes.append(node)
            for i in range(len(node.declarations)):
                node.declarations[i].parent = node
                node.declarations[i].index = i
        elif isinstance(node, FunctionDeclaration):
            self.scopes.append(node)
            for i in range(len(node.parameters)):
                node.parameters[i].parent = node
                node.parameters[i].index = i
        elif isinstance(node, LValue):
            if isinstance(node, ArrayLValue):
                # if an expression is used to index into the array, it will be transformed as we iterate over the tree
                pass
            elif isinstance(node, RecordLValue):
                # TODO eventually store records as arrays and index into the array here
                pass
            else:
                node.declaration = self.find_declaration(node.name, [VariableDeclaration, FunctionParameter])
        elif isinstance(node, FunctionCall):
            node.declaration = self.find_declaration(node.name, [FunctionDeclaration, NativeFunctionDeclaration])
        elif isinstance(node, TypeId):
            node.declaration = self.find_declaration(node.name, [TypeDeclaration])
        elif isinstance(node, ExitScope):
            self.scopes.pop()

    def find_declaration(self, name, expected_types):
        declaration = self.find(name, self.scopes)
        for expected_type in expected_types:
            if isinstance(declaration, expected_type):
                return declaration
        expected_types_string = '[%s]' % (', '.join([et.__name__ for et in expected_types]))
        raise ScopeError('Expected to find a declaration of type %s for name %s but instead found %s' % (
            expected_types_string, name, declaration.__class__.__name__))

    @staticmethod
    def find(name, scopes):
        # examine in reverse order
        for i in range(len(scopes) - 1, -1, -1):
            scope = scopes[i]
            if isinstance(scope, Let):
                for declaration in scope.declarations:
                    assert isinstance(declaration, Declaration)
                    if declaration.name == name:
                        return declaration
            elif isinstance(scope, FunctionDeclaration) or isinstance(scope, NativeFunctionDeclaration):
                # TODO RPython may not be able to handle this sort of unification
                if scope.name == name:
                    return scope
                for parameter in scope.parameters:
                    assert isinstance(parameter, FunctionParameter)
                    if parameter.name == name:
                        return parameter
            else:
                raise ScopeError('Unknown scope type; should be a Let or FunctionDeclaration: %s' % scope)

        raise ScopeError('Unable to find the name %s in the enclosing scopes' % name)
