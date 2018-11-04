from itertools import cycle


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
