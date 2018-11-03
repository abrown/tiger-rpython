import logging
import pickle
from os import listdir
from os.path import join

from src.benchmark.perf import analyze, run_command

# setup logging
logging.basicConfig(level=logging.INFO)

# gather data
path_to_interpreter = 'bin/tiger-interpreter'
path_to_benchmarks = 'src/benchmark/environment-comparison'
benchmark_programs = [join(path_to_benchmarks, file) for file in listdir(path_to_benchmarks) if file.endswith('.tig')]
data = [analyze(path_to_interpreter + ' ' + benchmark) for benchmark in benchmark_programs]

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
