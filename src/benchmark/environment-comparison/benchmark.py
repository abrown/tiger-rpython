import logging
import pickle
from os import listdir
from os.path import join

from src.benchmark.perf import analyze, run_command

# setup logging
logging.basicConfig(level=logging.INFO)

PATH_TO_INTERPRETER = 'bin/tiger-interpreter'
PATH_TO_BENCHMARKS = 'src/benchmark/suite-single'

# gather data
benchmark_programs = [join(PATH_TO_BENCHMARKS, filename) for filename in listdir(PATH_TO_BENCHMARKS) if
                      filename.endswith('.tig')]
data = [analyze(PATH_TO_INTERPRETER + ' ' + benchmark) for benchmark in benchmark_programs]

# find git branch
git_branch = run_command('git', 'rev-parse', '--abbrev-ref', 'HEAD')[0]
assert isinstance(git_branch, str)
git_branch = ''.join(git_branch.split())

# save data
path_to_pickled_data = 'var/environment-comparison-%s.pkl' % git_branch
logging.info("Saving data to: %s", path_to_pickled_data)
pickled_data_file = open(path_to_pickled_data, 'wb')
pickle.dump(data, pickled_data_file)
pickled_data_file.close()
