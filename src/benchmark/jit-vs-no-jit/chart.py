import logging
import os
import pickle

import matplotlib.pyplot as plt

from src.benchmark.charting import cycle_bar_styles

# setup logging
logging.basicConfig(level=logging.INFO)

PATH_TO_PICKLED_DATA = 'var/jit-vs-no-jit-vs-c.pkl'

# gather data from pickled files
with open(PATH_TO_PICKLED_DATA, 'rb') as f:
    results = pickle.load(f)

# find environment names
features = [env_name for env_name in results]
logging.info("Found features tested: %s" % features)

# find benchmark names
benchmark_names = list(results[features[0]].keys())
logging.info("Found benchmark names in first result set: %s" % benchmark_names)
for feature, benchmarks in results.iteritems():
    assert benchmark_names == benchmarks.keys()


def cycles(benchmark):
    return [b['cycles'] for (_, b) in benchmark.iteritems()]


def average_speedup(faster, slower):
    times_diff = [float(s) / float(f) for (s, f) in zip(slower, faster)]
    return reduce(lambda x, y: x * y, times_diff) ** (1.0 / len(times_diff))


# calculate average difference between environments
logging.info("Geometric mean of the speedup of C (O0) over JIT: %s",
             average_speedup(cycles(results['c-O0']), cycles(results['jit'])))
logging.info("Geometric mean of the speedup of C (O2) over JIT: %s",
             average_speedup(cycles(results['c-O2']), cycles(results['jit'])))
logging.info("Geometric mean of the speedup of JIT over non-JIT: %s",
             average_speedup(cycles(results['jit']), cycles(results['no-jit'])))

# draw plot

# necessary for LaTex PGF plots,
# see http://sbillaudelle.de/2015/02/23/seamlessly-embedding-matplotlib-output-into-latex.html
plt.rcParams['pgf.rcfonts'] = False

# bar plot adapted from https://matplotlib.org/gallery/statistics/barchart_demo.html
fig, ax = plt.subplots()

# draw bars
normalization_times = [m['cycles'] for (_, m) in results['jit'].iteritems()]
bar_width = 0.21
bar_offset = 0
bar_styles = cycle_bar_styles()
for feature, benchmarks in results.items():
    times = [float(m['cycles']) for (_, m) in benchmarks.iteritems()]
    logging.info("Raw times for %s: %s" % (feature, zip(benchmark_names, times)))
    normalized_times = [time / normalization_time for (time, normalization_time) in zip(times, normalization_times)]

    time_variance = [m['cycles-variance'] for (_, m) in benchmarks.iteritems()]
    logging.info("Raw variance for %s: %s" % (feature, zip(benchmark_names, time_variance)))
    error = [normalized_time * variance for (normalized_time, variance) in zip(normalized_times, time_variance)]

    logging.info("Creating bar for %s: %s (error: %s)" % (feature, normalized_times, error))

    # workaround for hatching, see https://stackoverflow.com/questions/5195466
    bar_indexes = [index + bar_width * bar_offset for index in range(len(benchmarks))]
    unhatched_style, hatched_style = next(bar_styles)
    ax.bar(bar_indexes, normalized_times, bar_width, yerr=error, **unhatched_style)
    ax.bar(bar_indexes, normalized_times, bar_width, yerr=error, label=feature, **hatched_style)
    # original color bar: ax.bar([index + bar_width * bar_offset for index in range(len(benchmarks))],
    #   normalized_times, bar_width, label=env)

    bar_offset += 1

ax.set_xlabel('Benchmarks')
ax.set_ylabel('CPU cycles (normalized to JIT, lower is better)')
ax.set_title('Benchmark Execution Times')
ax.set_xticks([index + bar_width * float(len(results) - 1) / 2 for index in range(len(benchmark_names))])
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
