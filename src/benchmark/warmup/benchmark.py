import logging
import os
import pickle
from collections import OrderedDict
from os import listdir
from os.path import join

import matplotlib.pyplot as plt

from src.benchmark.extract import extract_benchmark_name
from src.benchmark.perf import run_command

# setup logging
logging.basicConfig(level=logging.INFO)

# gather data
path_to_jit_interpreter = 'bin/tiger-interpreter'
path_to_benchmarks = 'src/benchmark/warmup'
benchmark_programs = [join(path_to_benchmarks, file_path) for file_path in listdir(path_to_benchmarks)
                      if file_path.endswith('.tig')]
data = OrderedDict()
for benchmark in benchmark_programs:
    name = extract_benchmark_name(benchmark)
    stdout, stderr = run_command(path_to_jit_interpreter, benchmark, env={'DEBUG': '1'})

    results = [int(s) for s in stdout.split("\n") if s]
    assert not results or all(x == results[0] for x in results), \
        'Expected all results to be the same %s, %s' % (results[0], results)

    loop_times = [int(s.replace('ticks=', '')) for s in stderr.split("\n") if s]
    logging.info("Raw loop times for %s benchmark: %s", name, loop_times)

    data[name] = loop_times

# save data
path_to_pickled_data = 'var/warmup.pkl'
logging.info("Saving data to: %s", path_to_pickled_data)
pickled_data_file = open(path_to_pickled_data, 'wb')
pickle.dump(data, pickled_data_file)
pickled_data_file.close()

# draw plot

# necessary for LaTex PGF plots,
# see http://sbillaudelle.de/2015/02/23/seamlessly-embedding-matplotlib-output-into-latex.html
plt.rcParams['pgf.rcfonts'] = False

# bar plot adapted from https://matplotlib.org/users/pyplot_tutorial.html
plt.figure(1)

# draw bars
num_rows = 2
num_columns = 3
i = 1
for name, loop_times in data.items():
    ax = plt.subplot(num_rows * 100 + num_columns * 10 + i)
    ax.set_title(name)
    ax.set_ylabel('CPU Ticks')
    ax.set_xlabel("Iterations")
    index = range(len(loop_times))
    plt.plot(index, loop_times, 'k')  # or 'k'
    i += 1

if os.getenv('SAVE', 0):
    # save files
    plt.savefig('var/warmup.pdf')
    plt.savefig('var/warmup.pgf')
    # use this in LaTex, see http://sbillaudelle.de/2015/02/23/seamlessly-embedding-matplotlib-output-into-latex.html
else:
    # display plot
    plt.show()
