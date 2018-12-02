from os import listdir
from os.path import basename, join


# TODO replace with BenchmarkMeasurement

def extract_benchmark_name(cmd):
    return basename(cmd).replace('.tig', '')


def extract_execution_time(results):
    return float(results['task-clock']['value'])


def extract_execution_time_variance(results):
    return float(results['task-clock']['variance'].replace('%', '')) / 100


def extract_file_name(path, prefix='', suffix='.tig'):
    return basename(path).replace(suffix, '').replace(prefix, '')


def collect_files(directory='var', prefix='', suffix='.tig'):
    """
    :param directory: the directory to collect files from
    :param prefix: a file name prefix, e.g. environment-comparison-
    :param suffix: a file name suffix, e.g. .tig
    :return:  a list of tuples of (extracted name, path to file)
    """
    return [(extract_file_name(file_path, prefix, suffix), join(directory, file_path))
            for file_path in listdir(directory) if
            file_path.startswith(prefix) and file_path.endswith(suffix)]
