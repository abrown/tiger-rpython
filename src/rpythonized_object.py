class RPythonizedObject:
    _attrs_ = []

    def __init__(self): pass

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

    def __ne__(self, other):
        return not self.equals(other)


def list_equals(list1, list2):
    """Helper function for comparing two iterable sequences of expressions using .equals()"""
    if len(list1) != len(list2):
        return False
    else:
        for i in range(len(list1)):
            if not list1[i].equals(list2[i]):
                print("not equal: %s" % list1[i].to_string())
                return False
    return True


def dict_equals(dict1, dict2):
    """Helper function for comparing two iterable sequences of expressions using .equals()"""
    if len(dict1) != len(dict2):
        return False
    else:
        for i in dict1:
            if not dict1[i].equals(dict2[i]):
                return False
    return True


def nullable_equals(obj1, obj2):
    if obj1 is None and obj2 is None:
        return True
    elif obj1 is not None and obj2 is not None:
        return obj1.equals(obj2)
    else:
        return False


def list_to_string(expression_list):
    stringified = []
    for item in expression_list:
        stringified.append(item.to_string())
    return '[%s]' % (', '.join(stringified))


def dict_to_string(expression_dict):
    stringified = []
    for key in expression_dict:
        stringified.append(key + '=' + expression_dict[key].to_string())
    return '{%s}' % (', '.join(stringified))


def nullable_to_string(obj):
    return obj.to_string() if obj is not None else 'None'
