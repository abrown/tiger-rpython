import logging
import os
import pickle
from collections import OrderedDict
from os import listdir
from os.path import join, basename

import matplotlib.pyplot as plt

from src.benchmark.charting import cycle_bar_styles
from src.benchmark.extract import extract_benchmark_name, extract_execution_time, extract_execution_time_variance

# setup logging

logging.basicConfig(level=logging.INFO)


# the charting is done separately from benchmark.py because we must gather benchmarks from different code branches in
# var/environment-comparison-*.pkl before charting them (some amount of manual work needed)

def extract_environment_name(path):
    return basename(path).replace('.pkl', '').replace('environment-comparison-', '')


# gather data from pickled files
path_to_pickled_data = 'var'
pickled_data_files = [join(path_to_pickled_data, file_path) for file_path in listdir(path_to_pickled_data) if
                      file_path.startswith('environment-comparison') and file_path.endswith('.pkl')]
pickled_data = OrderedDict()
for file_path in pickled_data_files:
    with open(file_path, 'rb') as f:
        pickled_data[extract_environment_name(file_path)] = pickle.load(f)

# find environment names
environments = [env_name for env_name in pickled_data]
logging.info("Found environment results in %s/*.pkl files: %s" % (path_to_pickled_data, environments))

# find benchmark names
benchmark_names = [extract_benchmark_name(cmd) for (cmd, _) in pickled_data[next(iter(pickled_data))]]
logging.info("Found benchmark names in first result set: %s" % benchmark_names)

# find the times used for normalizing all other times
normalization_branch = 'env-embedded-in-ast'
normalization_times = [extract_execution_time(results) for (_, results) in pickled_data[normalization_branch]]
logging.info("Found times to normalize by in '%s' result set: %s", normalization_branch, normalization_times)

# calculate average difference between environments
for env, benchmarks in pickled_data.items():
    times = [extract_execution_time(results) for (_, results) in benchmarks]
    times_diff = [time / normalization_time for (time, normalization_time) in zip(times, normalization_times)]
    geometric_mean = reduce(lambda x, y: x * y, times_diff) ** (1.0 / len(times_diff))
    logging.info("Geometric mean of the speedup of '%s' over %s: %s", normalization_branch, env, geometric_mean)

# draw plot

# necessary for LaTex PGF plots,
# see http://sbillaudelle.de/2015/02/23/seamlessly-embedding-matplotlib-output-into-latex.html
plt.rcParams['pgf.rcfonts'] = False

# bar plot adapted from https://matplotlib.org/gallery/statistics/barchart_demo.html
fig, ax = plt.subplots()

# draw bars
bar_width = 0.25
bar_offset = 0
bar_styles = cycle_bar_styles()
for env, benchmarks in pickled_data.items():
    names = [extract_benchmark_name(cmd) for (cmd, _) in benchmarks]
    assert names == benchmark_names, "Benchmarks must all be in the same order"

    times = [extract_execution_time(results) for (_, results) in benchmarks]
    normalized_times = [time / normalization_time for (time, normalization_time) in zip(times, normalization_times)]

    time_variance = [extract_execution_time_variance(results) for (_, results) in benchmarks]
    error = [normalized_time * variance for (normalized_time, variance) in zip(normalized_times, time_variance)]
    logging.info("Creating bar for %s: %s (error: %s)" % (env, times, error))

    # workaround for hatching, see https://stackoverflow.com/questions/5195466
    bar_indexes = [index + bar_width * bar_offset for index in range(len(benchmarks))]
    unhatched_style, hatched_style = next(bar_styles)
    ax.bar(bar_indexes, normalized_times, bar_width, yerr=error, **unhatched_style)
    ax.bar(bar_indexes, normalized_times, bar_width, yerr=error, label=env, **hatched_style)
    # original color bar: ax.bar([index + bar_width * bar_offset for index in range(len(benchmarks))],
    #   normalized_times, bar_width, label=env)

    bar_offset += 1

ax.set_xlabel('Benchmarks')
ax.set_ylabel('Task time (normalized to embedded, lower is better)')
ax.set_title('Benchmark Task Times by Environment Implementation')
ax.set_xticks([index + bar_width * (len(pickled_data) - 1) / 2 for index in range(len(benchmark_names))])
ax.set_xticklabels(benchmark_names)
ax.legend(loc=2)  # re-enable if we keep ax.bar(..., label='...')
fig.tight_layout()  # necessary to re-position axis labels

if os.getenv('SAVE', 0):
    # save files
    plt.savefig('var/environment-comparison.pdf')
    plt.savefig('var/environment-comparison.pgf')
    # use this in LaTex, see http://sbillaudelle.de/2015/02/23/seamlessly-embedding-matplotlib-output-into-latex.html
else:
    # display plot
    plt.show()
