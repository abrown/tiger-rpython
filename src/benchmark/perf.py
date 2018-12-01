import csv
import logging
import subprocess

# setup logging
from collections import OrderedDict

from src.benchmark.measurement import BenchmarkMeasurement

logging.basicConfig(level=logging.INFO)


def run_command(*args, **kwargs):
    """
    Run a command, capturing the output
    :param args: a vararg list of the command to run
    :param kwargs: any additional options to pass unmodified to popen, see https://docs.python.org/2/library/subprocess.html#subprocess.Popen
    :return: a tuple with the (stdout, stderr) strings or an exception is thrown
    """
    logging.info("Running: %s", ' '.join(args))
    pipes = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    stdout, stderr = pipes.communicate()
    if pipes.returncode != 0:
        # print stderr, stdout?
        raise Exception("Failed to run command (code: %d): %s" % (pipes.returncode, args))
    return stdout, stderr


def run_perf_on(*args, **kwargs):
    """
    Run a command from within 'perf'; see https://perf.wiki.kernel.org/index.php/Tutorial; note: it would not be hard
    to add or remove events with '-e'
    :param args: a vararg list of the command to run
    :return: a tuple with the (stdout, stderr) strings or an exception is thrown
    """
    number_of_iterations_to_run = kwargs.pop('iterate', 5)
    perf_args = ['perf', 'stat', '-x;', '-r ' + str(number_of_iterations_to_run)]
    perf_args.extend(args)
    return run_command(*perf_args, **kwargs)


def parse_perf_output(output):
    """
    Parse the 'perf' output to something Python-friendly; it expects a ';' delimiter
    :param output: the 'perf' output string
    :return: a dictionary keyed by event, e.g. cycles; each key contains another dictionary with the fields below (from 
    http://man7.org/linux/man-pages/man1/perf-stat.1.html):
        With -x, perf stat is able to output a not-quite-CSV format output. Commas in the output are not put into "".
        To make it easy to parse it is recommended to use a different character like -x \;
        The fields are in this order:
        -   optional usec time stamp in fractions of second (with -I xxx)
        -   optional CPU, core, or socket identifier
        -   optional number of logical CPUs aggregated
        -   counter value
        -   unit of the counter value or empty
        -   event name
        -   run time of counter
        -   percentage of measurement time the counter was running
        -   optional variance if multiple values are collected with -r
        -   optional metric value
        -   optional unit of metric
        Additional metrics may be printed with all earlier fields being empty.
    """
    output = output.split('\n')
    fields = ['value', 'unit', 'event', 'variance', 'counter_runtime', 'counter_percentage_of_runtime', 'metric_value',
              'metric_unit']
    rows = csv.DictReader(output, fields, delimiter=';')

    measurements = OrderedDict()
    for row in rows:
        event = row['event'].replace(':u', '')
        measurements[event] = row
    return measurements


def analyze(command, wrap_measurements=False):
    """
    :param command: a string version of the command, e.g. 'curl -s http://google.com'
    :return: a tuple with the command string and the measurements taken from running it, e.g.
    ('ls', {'task-clock': {'value': '52.5', ...}, 'instructions': {...}, ...})
    """
    args = command.split(' ')
    stdout, stderr = run_perf_on(*args)
    measurements = parse_perf_output(stderr)

    for key in measurements:
        logging.info('Command `%s` has measurement %s = %s', command, key, measurements[key]['value'])
        logging.debug('Command `%s` has additional details for %s: %s', command, key, measurements[key])

    if wrap_measurements:
        return BenchmarkMeasurement(command, measurements)
    else:
        return command, measurements
