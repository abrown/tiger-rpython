import logging
import os
import pickle

import matplotlib.pyplot as plt

# setup logging
logging.basicConfig(level=logging.INFO)

PATH_TO_PICKLED_DATA = 'var/warmup.pkl'

# gather data
logging.info("Collection data from: %s", PATH_TO_PICKLED_DATA)
with open(PATH_TO_PICKLED_DATA, 'rb') as f:
    data = pickle.load(f)


# show variance
for name, loop_times in data.items():
    mean = sum(loop_times) / len(loop_times)
    error = sum([abs(float(c - mean)) for c in loop_times]) / len(loop_times) / mean
    logging.info("Benchmark %s executed on average %s cycles with a %s%% error", name, mean, round(error * 100, 3))
    logging.info("Benchmark %s executed the first iteration %s%% away from average", name, round((loop_times[0] - mean) / float(mean) * 100, 3))

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
    ax.set_ylabel('CPU Cycles')
    ax.set_xlabel("Iterations")
    index = range(len(loop_times))
    plt.plot(index, loop_times, 'k')  # or 'k'
    i += 1

plt.tight_layout()  # necessary to re-position axis labels

if os.getenv('SAVE', 0):
    # save files
    plt.savefig('var/warmup.pdf')
    plt.savefig('var/warmup.pgf')
    # use this in LaTex, see http://sbillaudelle.de/2015/02/23/seamlessly-embedding-matplotlib-output-into-latex.html
else:
    # display plot
    plt.show()
