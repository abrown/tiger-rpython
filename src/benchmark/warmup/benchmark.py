import logging
import pickle
from collections import OrderedDict

from src.benchmark.extract import collect_files
from src.benchmark.perf import run_command

# setup logging
logging.basicConfig(level=logging.INFO)

PATH_TO_JIT_INTERPRETER = 'bin/tiger-interpreter'
PATH_TO_BENCHMARKS = 'src/benchmark/suite-looped'
PATH_TO_PICKLED_DATA = 'var/warmup.pkl'
PATH_TO_PYPYLOG = 'jit:var/%s-convoluted.log'

# gather data
benchmark_programs = collect_files(PATH_TO_BENCHMARKS, suffix='.tig')

data = OrderedDict()
for name, program in benchmark_programs:
    log = PATH_TO_PYPYLOG % name
    stdout, stderr = run_command(PATH_TO_JIT_INTERPRETER, program,
                                 env={'DEBUG': '1', 'PYPYLOG': log})

    results = [int(s) for s in stdout.split("\n") if s]
    assert not results or all(x == results[0] for x in results), \
        'Expected all results to be the same %s, %s' % (results[0], results)

    loop_times = [int(s.replace('ticks=', '')) for s in stderr.split("\n") if s]
    logging.info("Raw loop times for %s benchmark: %s", name, loop_times)

    data[name] = loop_times

# save data
logging.info("Saving data to: %s", PATH_TO_PICKLED_DATA)
pickled_data_file = open(PATH_TO_PICKLED_DATA, 'wb')
pickle.dump(data, pickled_data_file)
pickled_data_file.close()
