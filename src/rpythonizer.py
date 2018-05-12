import re
import sys

if len(sys.argv) < 2:
    raise RuntimeError('Expected a file argument: python rpythonizer.py some_file.py')


def debug(str):
    pass
    # print('[DEBUG] ' + str)


def generate_functions(fields):
    str = ('    def to_string(self):\n'
           "        return '%s(" + ', '.join([f + '=%s' for f in fields]) + ")' % (self.__class__.__name__, " + ', '.join(['self.' + f + '.to_string()' for f in fields]) + ")\n"
           "\n"
           "    def equals(self, other):\n"
           "        return RPythonizedObject.equals(self, other) and " + ' and '.join(['self.' + f + '.equals(other.' + f + ')' for f in fields]) + "\n")
    print(str)


with open(sys.argv[1], 'r') as lines:
    line_number = 0
    recording_fields = 0
    fields = []

    for line in lines:
        print(line[:-1])
        line_number += 1
        if recording_fields:
            if not line.strip():
                debug('Ending lines: ' + str(fields))
                generate_functions(fields)
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
