import logging
import pickle
from collections import OrderedDict

from src.benchmark.measurement import BenchmarkMeasurement
from src.benchmark.perf import analyze, run_perf_on, parse_perf_output

# setup logging
logging.basicConfig(level=logging.INFO)

BENCHMARKS = ['permute', 'queens', 'sieve', 'sumprimes', 'towers']
PATH_TO_BIN = 'bin'
PATH_TO_BENCHMARKS = 'src/benchmark/warmup'
PATH_TO_PICKLED_DATA = 'var/jit-vs-no-jit-vs-c.pkl'

results = OrderedDict()

# add C benchmarks (O0 and O2)
for feature in ['O0', 'O2']:
    feature_key = 'c-' + feature
    results[feature_key] = OrderedDict()
    for benchmark in BENCHMARKS:
        program = '%s/%s-%s' % (PATH_TO_BIN, benchmark, feature)
        measurements = analyze(program, True)
        measurements.assert_no_os_interference()
        results[feature_key][benchmark] = OrderedDict([('cycles', measurements.get_as_int('cycles')),
                                                       ('cycles-variance', measurements.get_variance('cycles')),
                                                       ('time-ms', measurements.get_as_float('task-clock')),
                                                       ('time-variance', measurements.get_variance('task-clock')),
                                                       ])

# add RPython benchmarks (jit and no-jit)
for feature in ['jit', 'no-jit']:
    results[feature] = OrderedDict()
    for benchmark in BENCHMARKS:
        interpreter = '%s/tiger-interpreter-no-jit' % PATH_TO_BIN
        program = '%s/%s.tig' % (PATH_TO_BENCHMARKS, benchmark)
        stdout, stderr = run_perf_on(interpreter, program, env={'DEBUG': '1'}, iterate=1)

        program_results = [int(s) for s in stdout.split("\n") if s]
        assert not program_results or all(x == program_results[0] for x in program_results), \
            'Expected all results to be the same %s, %s' % (program_results[0], program_results)

        cycles = [int(s.replace('ticks=', '')) for s in stderr.split("\n") if s.startswith('ticks=')]
        logging.debug("Raw loop times for %s benchmark: %s", benchmark, cycles)

        parsed = parse_perf_output('\n'.join([s for s in stderr.split("\n") if not s.startswith('ticks=')]))
        measurements = BenchmarkMeasurement(interpreter + ' ' + program, parsed)
        logging.info("Total time for %s benchmark: %sms (%s total perf cycles ?= %s summed iteration cycles)",
                     benchmark,
                     measurements.get_as_float('task-clock'), measurements.get_as_int('cycles'), sum(cycles))
        measurements.assert_no_os_interference()

        last_five_iterations = cycles[-5:]
        logging.debug("Raw loop times for the last five iterations of %s benchmark: %s", benchmark,
                      last_five_iterations)
        cycles_mean = sum(last_five_iterations) / len(last_five_iterations)
        cycles_error = sum([abs(float(c - cycles_mean)) for c in last_five_iterations]) / len(
            last_five_iterations) / cycles_mean
        cycles_variance = sum([(c - cycles_mean) ** 2 for c in last_five_iterations]) / (len(
            last_five_iterations) - 1)  # TODO is this correct? and does it map to perf's percentage variance?
        logging.info("Average cycles for last five iterations of %s benchmark: %s (variance = %s)", benchmark,
                     cycles_mean, cycles_error)

        results[feature][benchmark] = OrderedDict([('cycles', cycles_mean),
                                                   ('cycles-variance', cycles_error),
                                                   ])

# save data
logging.info("Saving data to: %s", PATH_TO_PICKLED_DATA)
pickled_data_file = open(PATH_TO_PICKLED_DATA, 'wb')
pickle.dump(results, pickled_data_file)
pickled_data_file.close()
