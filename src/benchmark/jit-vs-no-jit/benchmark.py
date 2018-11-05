import logging
import pickle
from collections import OrderedDict
from os import listdir
from os.path import join, basename

import matplotlib.pyplot as plt

from src.benchmark.charting import cycle_bar_styles
from src.benchmark.perf import analyze, run_command

# setup logging
logging.basicConfig(level=logging.INFO)


def extract_environment_name(file):
    return basename(file).replace('.pkl', '').replace('environment-comparison-', '')


def extract_benchmark_name(cmd):
    return basename(cmd).replace('.tig', '')


def extract_execution_time(results):
    return float(results['task-clock']['value'])


def extract_execution_time_variance(results):
    return float(results['task-clock']['variance'].replace('%', '')) / 100


# gather data
path_to_jit_interpreter = 'bin/tiger-interpreter'
path_to_no_jit_interpreter = 'bin/tiger-interpreter-no-jit'
path_to_benchmarks = 'src/benchmark/jit-vs-no-jit'
benchmark_programs = [join(path_to_benchmarks, file) for file in listdir(path_to_benchmarks) if file.endswith('.tig')]
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

# draw plot

# necessary for LaTex PGF plots, see http://sbillaudelle.de/2015/02/23/seamlessly-embedding-matplotlib-output-into-latex.html
plt.rcParams['pgf.rcfonts'] = False

# bar plot adapted from https://matplotlib.org/gallery/statistics/barchart_demo.html
fig, ax = plt.subplots()

# draw bars
bar_width = 0.25
bar_offset = 0
bar_styles = cycle_bar_styles()
for env, benchmarks in data.items():
    names = [extract_benchmark_name(cmd) for (cmd, _) in benchmarks]
    assert names == benchmark_names, "Benchmarks must all be in the same order"

    times = [extract_execution_time(results) for (_, results) in benchmarks]
    time_variance = [extract_execution_time_variance(results) for (_, results) in benchmarks]
    error = [time * variance for (time, variance) in zip(times, time_variance)]
    logging.info("Creating bar for %s: %s (error: %s)" % (env, times, error))

    # workaround for hatching, see https://stackoverflow.com/questions/5195466
    bar_indexes = [index + bar_width * bar_offset for index in range(len(benchmarks))]
    unhatched_style, hatched_style = next(bar_styles)
    ax.bar(bar_indexes, times, bar_width, yerr=error, **unhatched_style)
    ax.bar(bar_indexes, times, bar_width, yerr=error, label=env, **hatched_style)
    # original color bar: ax.bar([index + bar_width * bar_offset for index in range(len(benchmarks))], normalized_times, bar_width, label=env)

    bar_offset += 1

ax.set_xlabel('Benchmarks')
ax.set_ylabel('Task time in seconds (lower is better)')
ax.set_title('Benchmark Task Times with JIT enabled/disabled')
ax.set_xticks([index + bar_width * (len(data) - 1) / 2 for index in range(len(benchmark_names))])
ax.set_xticklabels(benchmark_names)
ax.legend()  # re-enable if we keep ax.bar(..., label='...')
fig.tight_layout()  # necessary to re-position axis labels

# display plot
plt.show()

# save files
# plt.savefig('var/jit-vs-no-jit.pdf')
# plt.savefig('var/jit-vs-no-jit.pgf')  # use this in LaTex, see http://sbillaudelle.de/2015/02/23/seamlessly-embedding-matplotlib-output-into-latex.html
