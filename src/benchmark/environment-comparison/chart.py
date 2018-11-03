import logging
import pickle
from itertools import cycle
from os import listdir
from os.path import join, basename

import matplotlib.pyplot as plt

# setup logging
logging.basicConfig(level=logging.INFO)

# gather data
path_to_pickled_data = 'var'
pickled_data_files = [join(path_to_pickled_data, file) for file in listdir(path_to_pickled_data) if
                      file.endswith('.pkl')]
data = {}
for file in pickled_data_files:
    with open(file, 'rb') as f:
        data[basename(file).replace('.pkl', '')] = pickle.load(f)

# setup chart (TODO multiple bars per benchmark)
bar_indexes = range(len(data))
x_values = [basename(name).replace('.tig', '') for (name, _) in data]  # the command names
y_values = [float(m['task-clock']['value']) for (name, m) in data]  # the task-times


# setup styles
def cycle_bar_styles():
    """
    Monochrome bar styles adapted from from http://olsgaard.dk/monochrome-black-white-plots-in-matplotlib.html
    :return: yields an infinite list of unhatched and hatched dictionaries of bar plot settings
    """
    hatch_marks = cycle(['///', '--', '...', '\///', 'xxx', '\\\\'])
    for hatch in hatch_marks:
        unhatched = {'color': 'w'}
        hatched = unhatched.copy()
        hatched.update({'hatch': hatch, 'edgecolor': 'k', 'zorder': [10]})
        yield unhatched, hatched


# draw plot

# necessary for LaTex PGF plots, see http://sbillaudelle.de/2015/02/23/seamlessly-embedding-matplotlib-output-into-latex.html
plt.rcParams['pgf.rcfonts'] = False

# bar plot adapted from https://matplotlib.org/gallery/statistics/barchart_demo.html
fig, ax = plt.subplots()

bar_width = 0.35
bar_styles = cycle_bar_styles()
for i in bar_indexes:
    unhatched_style, hatched_style = next(bar_styles)
    # workaround for hatching, see https://stackoverflow.com/questions/5195466
    ax.bar(i, y_values[i], bar_width, **unhatched_style)
    ax.bar(i, y_values[i], bar_width, **hatched_style)

# otherwise, the bars could all have the same style
# bars = ax.bar(index, task_times, bar_width, alpha=opacity, color='g', label='Task Times')

ax.set_xlabel('Tasks')
ax.set_ylabel('Times')
ax.set_title('Task Times')
ax.set_xticks([i for i in bar_indexes])
ax.set_xticklabels(x_values)
# ax.legend()  # re-enable if we keep ax.bar(..., label='...')
fig.tight_layout()  # necessary to re-position axis labels

# display plot
plt.show()

# save files
# plt.savefig('example.pdf')
# plt.savefig('example.pgf')  # use this in LaTex, see http://sbillaudelle.de/2015/02/23/seamlessly-embedding-matplotlib-output-into-latex.html
