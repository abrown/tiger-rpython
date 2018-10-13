import os
import re
import sys

if len(sys.argv) != 2:
    os.write(sys.stderr, "Usage: python extract-log-section.py [pattern], e.g. pattern == jit-log-opt")
    exit(1)

pattern = sys.argv[1]
beforePattern = re.compile('{' + pattern)
afterPattern = re.compile(pattern + '}')
lineNumberPattern = re.compile('\s*\+\d+:')

insideMatch = False
for line in sys.stdin:
    if insideMatch:
        formattedLine = re.sub(lineNumberPattern, '', line)
        sys.stdout.write(formattedLine)
        if afterPattern.search(line):
            insideMatch = False
    else:
        if beforePattern.search(line):
            insideMatch = True
