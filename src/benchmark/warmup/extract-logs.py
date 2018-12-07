import logging
import re
from collections import OrderedDict

# setup logging
logging.basicConfig(level=logging.INFO)

BENCHMARKS = ['permute', 'queens', 'sieve', 'sumprimes', 'towers']
PATH_TO_LOGS = 'var'
JITLOG_BLOCK = 'jit-summary'

for benchmark in BENCHMARKS:
    path = '%s/%s.log' % (PATH_TO_LOGS, benchmark)
    with open(path, 'r') as f:
        logs = f.read()

    pattern = re.compile('\{jit-summary(.*)jit-summary\}', re.MULTILINE | re.DOTALL)
    match = pattern.search(logs)
    summary = match.group(1)
    logging.debug('Entire summary: %s', summary)

    data = OrderedDict()
    data['tracing'] = re.search('Tracing:\s+\d+\s+([\d.]+)', summary).group(1)
    data['backend'] = re.search('Backend:\s+\d+\s+([\d.]+)', summary).group(1)
    data['total'] = re.search('TOTAL:\s+([\d.]+)', summary).group(1)
    # data['ops'] = re.search('ops:\s+(\d+)', summary).group(1)
    data['loops'] = re.search('Total # of loops:\s+(\d+)', summary).group(1)
    data['bridges'] = re.search('Total # of bridges:\s+(\d+)', summary).group(1)
    # logging.info("%s has stats: %s", benchmark, data)

    sep = ' & '
    print benchmark + sep + sep.join(data.values()) + ' \\\\'
    print '\hline'
