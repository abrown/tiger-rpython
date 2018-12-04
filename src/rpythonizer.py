# NOTE: we keep imports inside their functions to avoid any translation issues with RPython

def list_classes_in_file(parent_class=None):
    import inspect
    import sys
    assert not parent_class or inspect.isclass(parent_class), "Expected the passed parent_class to be a class itself"

    def class_filter(c):
        return inspect.isclass(c) and (not parent_class or issubclass(c, parent_class))

    return inspect.getmembers(sys.modules[__name__], class_filter)


def list_arguments_of_function(func, containing_class=None):
    import inspect
    args, arglist, keywords, defaults = inspect.getargspec(func)
    assert arglist is None, "Avoid using argument lists (e.g. *args) in constructor of class %s" % containing_class
    assert keywords is None, "Avoid using keywords (e.g. **kw) in constructor of class %s" % containing_class
    return args


def inject_logging_into_evaluate_methods():
    """
    In order to avoid cluttering the AST implementation with logging calls, this function will:
    1. examine all classes in this module
    2. if the class has an 'evaluate' attribute, replace it with a wrapper to print the string representation of the
    AST node
    :return: nothing
    """
    from functools import wraps

    def wrapper(method):
        @wraps(method)
        def wrapped(*args, **kwrds):
            self = args[0]
            env = args[1]
            if env and hasattr(env, 'debug') and env.debug:
                print(self.to_string())
            return method(*args, **kwrds)

        return wrapped

    for name, klass in list_classes_in_file():
        if 'evaluate' in klass.__dict__:
            # print('Replacing evaluate method of %s' % klass)
            setattr(klass, 'evaluate', wrapper(klass.__dict__['evaluate']))


def has_init_function(klass):
    return '__init__' in klass.__dict__ and hasattr(klass.__dict__['__init__'], '__call__')


def get_init_function(klass):
    return klass.__dict__['__init__']


def add_immutable_fields(klass):
    # init_name = '__init__'
    immutable_fields_name = '_immutable_fields_'
    # if hasattr(klass, init_name) and not hasattr(klass, immutable_fields_name):
    if has_init_function(klass) and immutable_fields_name not in klass.__dict__:
        args = [arg for arg in list_arguments_of_function(get_init_function(klass), klass.__name__) if arg != 'self']
        # TODO format list-like args, e.g. 'expressions[*]'
        print('Added _immutable_fields_ to %s: %s' % (klass.__name__, args))
        setattr(klass, immutable_fields_name, args)


def add_attrs(klass):
    attrs_name = '_attrs_'
    if attrs_name not in klass.__dict__:
        if has_init_function(klass):
            args = [arg for arg in list_arguments_of_function(get_init_function(klass), klass.__name__) if
                    arg != 'self']
        else:
            args = []
        setattr(klass, attrs_name, args)
        print('Added _attrs_ to %s: %s' % (klass.__name__, args))


def add_binary_operation_equals(klass):
    func_name = 'equals'
    if func_name not in klass.__dict__:
        def func(self, other):
            return isinstance(other, klass) and self.left.equals(other.left) and self.right.equals(other.right)

        setattr(klass, func_name, func)
        print('Added %s to %s' % (func_name, klass.__name__))


def always_equals_false(self, other):
    return False


def generate_functions(fields):
    """
    Helper method for creating textual representations of to_string and equals methods
    :param fields: the fields of a class
    :return: stringified RPython code with to_string and equals methods
    """
    code = ('    def to_string(self):\n'
            "        return '%s("
            + ', '.join([f + '=%s' for f in fields]) + ")' % (self.__class__.__name__, "
            + ', '.join(['self.' + f + '.to_string()' for f in fields])
            + ")\n"
              "\n"
              "    def equals(self, other):\n"
              "        return RPythonizedObject.equals(self, other) and "
            + ' and '.join(['self.' + f + '.equals(other.' + f + ')' for f in fields]) + "\n")
    return code


def convert_file(filepath):
    """
    Apply generate_functions to a file
    :param filepath: the file to convert
    :return: will print the converted file
    """
    import re

    def debug(message):
        assert isinstance(message, str)
        # print('[DEBUG] ' + message)
        pass

    with open(filepath, 'r') as lines:
        line_number = 0
        recording_fields = 0
        fields = []

        for line in lines:
            print(line[:-1])
            line_number += 1
            if recording_fields:
                if not line.strip():
                    debug('Ending lines: ' + str(fields))
                    print generate_functions(fields)
                    recording_fields = 0
                    fields = []
                else:
                    match = re.search('self\.(\w+) = ', line)
                    if match:
                        field = match.group(1)
                        debug('Found field: ' + field)
                        fields.append(field)
            elif not recording_fields and re.search('def __init__\(self, \w+', line):
                debug('Found __init__: ' + line)
                recording_fields = 1
