import logging
import os
import pickle
from collections import OrderedDict
from os import listdir
from os.path import join

import matplotlib.pyplot as plt

from src.benchmark.charting import cycle_bar_styles
from src.benchmark.extract import extract_benchmark_name, extract_execution_time, extract_execution_time_variance
from src.benchmark.perf import analyze

# setup logging
logging.basicConfig(level=logging.INFO)

# gather data
path_to_jit_interpreter = 'bin/tiger-interpreter'
path_to_no_jit_interpreter = 'bin/tiger-interpreter-no-jit'
path_to_benchmarks = 'src/benchmark/jit-vs-no-jit'
benchmark_programs = [join(path_to_benchmarks, file_path) for file_path in listdir(path_to_benchmarks)
                      if file_path.endswith('.tig')]
data = OrderedDict()
data['jit'] = [analyze(path_to_jit_interpreter + ' ' + benchmark) for benchmark in benchmark_programs]
data['no-jit'] = [analyze(path_to_no_jit_interpreter + ' ' + benchmark) for benchmark in benchmark_programs]

# save data
path_to_pickled_data = 'var/jit-vs-no-jit.pkl'
logging.info("Saving data to: %s", path_to_pickled_data)
pickled_data_file = open(path_to_pickled_data, 'wb')
pickle.dump(data, pickled_data_file)
pickled_data_file.close()

# find environment names
environments = [env_name for env_name in data]
logging.info("Found environments: %s" % environments)

# find benchmark names
benchmark_names = [extract_benchmark_name(cmd) for (cmd, _) in data[environments[0]]]
logging.info("Found benchmark names in first result set: %s" % benchmark_names)

# calculate average difference between environments
jit_times = [extract_execution_time(results) for (_, results) in data['jit']]
no_jit_times = [extract_execution_time(results) for (_, results) in data['no-jit']]
times_diff = [no_jit / jit for (no_jit, jit) in zip(no_jit_times, jit_times)]
geometric_mean = reduce(lambda x, y: x * y, times_diff) ** (1.0 / len(times_diff))
logging.info("Geometric mean of the speedup of JIT over non-JIT: %s", geometric_mean)


# draw plot

# necessary for LaTex PGF plots,
# see http://sbillaudelle.de/2015/02/23/seamlessly-embedding-matplotlib-output-into-latex.html
plt.rcParams['pgf.rcfonts'] = False

# bar plot adapted from https://matplotlib.org/gallery/statistics/barchart_demo.html
fig, ax = plt.subplots()

# draw bars
normalization_times = [extract_execution_time(results) for (_, results) in data['jit']]
bar_width = 0.25
bar_offset = 0
bar_styles = cycle_bar_styles()
for env, benchmarks in data.items():
    names = [extract_benchmark_name(cmd) for (cmd, _) in benchmarks]
    assert names == benchmark_names, "Benchmarks must all be in the same order"

    times = [extract_execution_time(results) for (_, results) in benchmarks]
    logging.info("Raw times: %s" % zip(names, times))
    normalized_times = [time / normalization_time for (time, normalization_time) in zip(times, normalization_times)]

    time_variance = [extract_execution_time_variance(results) for (_, results) in benchmarks]
    logging.info("Raw variance: %s" % zip(names, time_variance))
    error = [normalized_time * variance for (normalized_time, variance) in zip(normalized_times, time_variance)]

    logging.info("Creating bar for %s: %s (error: %s)" % (env, normalized_times, error))

    # workaround for hatching, see https://stackoverflow.com/questions/5195466
    bar_indexes = [index + bar_width * bar_offset for index in range(len(benchmarks))]
    unhatched_style, hatched_style = next(bar_styles)
    ax.bar(bar_indexes, normalized_times, bar_width, yerr=error, **unhatched_style)
    ax.bar(bar_indexes, normalized_times, bar_width, yerr=error, label=env, **hatched_style)
    # original color bar: ax.bar([index + bar_width * bar_offset for index in range(len(benchmarks))],
    #   normalized_times, bar_width, label=env)

    bar_offset += 1

ax.set_xlabel('Benchmarks')
ax.set_ylabel('Task time normalized to JIT (lower is better)')
ax.set_title('Benchmark Task Times with JIT enabled/disabled')
ax.set_xticks([index + bar_width * (len(data) - 1) / 2 for index in range(len(benchmark_names))])
ax.set_xticklabels(benchmark_names)
ax.legend()  # re-enable if we keep ax.bar(..., label='...')
fig.tight_layout()  # necessary to re-position axis labels

if os.getenv('SAVE', 0):
    # save files
    plt.savefig('var/jit-vs-no-jit.pdf')
    plt.savefig('var/jit-vs-no-jit.pgf')
    # use this in LaTex, see http://sbillaudelle.de/2015/02/23/seamlessly-embedding-matplotlib-output-into-latex.html
else:
    # display plot
    plt.show()
