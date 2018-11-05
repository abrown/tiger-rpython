import os

# print out the benchmark code in a LaTex-compatible format
directory = os.path.dirname(os.path.realpath(__file__))
benchmarks = [file for file in os.listdir(directory) if file.endswith('.tig')]
for benchmark in benchmarks:
    print '\\begin{lstlisting}[caption=%s]' % benchmark
    fd = open(os.path.join(directory, benchmark), 'r')
    print fd.read()
    fd.close()
    print '\\end{lstlisting}'
    print
