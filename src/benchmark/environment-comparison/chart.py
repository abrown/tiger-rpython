import logging
import pickle
from collections import OrderedDict
from os import listdir
from os.path import join, basename

import matplotlib.pyplot as plt

from src.benchmark.charting import cycle_bar_styles

# setup logging
logging.basicConfig(level=logging.INFO)


def extract_environment_name(file):
    return basename(file).replace('.pkl', '').replace('environment-comparison-', '')


def extract_benchmark_name(cmd):
    return basename(cmd).replace('.tig', '')


def extract_execution_time(results):
    return float(results['task-clock']['value'])


# gather data from pickled files
path_to_pickled_data = 'var'
pickled_data_files = [join(path_to_pickled_data, file) for file in listdir(path_to_pickled_data) if
                      file.endswith('.pkl')]
pickled_data = OrderedDict()
for file in pickled_data_files:
    with open(file, 'rb') as f:
        pickled_data[extract_environment_name(file)] = pickle.load(f)

# find environment names
environments = [env_name for env_name in pickled_data]
logging.info("Found environments in %s/*.pkl files: %s" % (path_to_pickled_data, environments))

# find benchmark names
benchmark_names = [extract_benchmark_name(cmd) for (cmd, _) in pickled_data[next(iter(pickled_data))]]
logging.info("Found benchmark names in first result set: %s" % benchmark_names)

# find the times used for normalizing all other times
normalization_times = [extract_execution_time(results) for (_, results) in pickled_data['master']]
logging.info("Found times to normalize by in 'master' result set: %s" % normalization_times)



# draw plot

# necessary for LaTex PGF plots, see http://sbillaudelle.de/2015/02/23/seamlessly-embedding-matplotlib-output-into-latex.html
plt.rcParams['pgf.rcfonts'] = False

# bar plot adapted from https://matplotlib.org/gallery/statistics/barchart_demo.html
fig, ax = plt.subplots()

# draw bars
bar_width = 0.25
bar_offset = 0
bar_styles = cycle_bar_styles()
for env, benchmarks in pickled_data.items():
    names = [extract_benchmark_name(cmd) for (cmd, results) in benchmarks]
    assert names == benchmark_names, "Benchmarks must all be in the same order"

    times = [extract_execution_time(results) for (cmd, results) in benchmarks]
    logging.info("Creating bar for %s: %s" % (env, times))

    normalized_times = [time / normalization_time for (time, normalization_time) in zip(times, normalization_times)]

    # workaround for hatching, see https://stackoverflow.com/questions/5195466
    bar_indexes = [index + bar_width * bar_offset for index in range(len(benchmarks))]
    unhatched_style, hatched_style = next(bar_styles)
    ax.bar(bar_indexes, normalized_times, bar_width, **unhatched_style)
    ax.bar(bar_indexes, normalized_times, bar_width, label=env, **hatched_style)
    # original color bar: ax.bar([index + bar_width * bar_offset for index in range(len(benchmarks))], normalized_times, bar_width, label=env)

    bar_offset += 1

ax.set_xlabel('Benchmarks')
ax.set_ylabel('Task time (normalized to master, lower is better)')
ax.set_title('Benchmark Task Times by Environment Implementation')
ax.set_xticks([index + bar_width * (len(pickled_data) - 1) / 2 for index in range(len(benchmark_names))])
ax.set_xticklabels(benchmark_names)
ax.legend()  # re-enable if we keep ax.bar(..., label='...')
fig.tight_layout()  # necessary to re-position axis labels

# display plot
plt.show()

# save files
# plt.savefig('example.pdf')
# plt.savefig('example.pgf')  # use this in LaTex, see http://sbillaudelle.de/2015/02/23/seamlessly-embedding-matplotlib-output-into-latex.html
