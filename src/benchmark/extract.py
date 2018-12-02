from os.path import basename

# TODO replace with BenchmarkMeasurement

def extract_benchmark_name(cmd):
    return basename(cmd).replace('.tig', '')


def extract_execution_time(results):
    return float(results['task-clock']['value'])


def extract_execution_time_variance(results):
    return float(results['task-clock']['variance'].replace('%', '')) / 100
