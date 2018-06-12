./src/benchmark/benchmark.sh src/benchmark/while-100k.tig;  ./src/benchmark/benchmark.sh src/benchmark/while-10k.tig;  ./src/benchmark/benchmark.sh src/benchmark/while-1k.tig;  ./src/benchmark/benchmark.sh src/benchmark/while-1m.tig;
python src/main/tiger-interpreter.py src/benchmark/while-100k.tig
	Time: 0.54user 0.00system 0:00.55elapsed 99%CPU (0avgtext+0avgdata 7548maxresident)k 0inputs+0outputs (0major+1011minor)pagefaults 0swaps
	Code: 0
	Value: IntegerValue(100000)

bin/tiger-interpreter-no-jit src/benchmark/while-100k.tig
	Time: 0.00user 0.00system 0:00.02elapsed 43%CPU (0avgtext+0avgdata 6112maxresident)k 0inputs+0outputs (0major+1141minor)pagefaults 0swaps
	Code: 0
	Value: IntegerValue(100000)

bin/tiger-interpreter src/benchmark/while-100k.tig
	Time: 0.01user 0.00system 0:00.01elapsed 100%CPU (0avgtext+0avgdata 9928maxresident)k 0inputs+64outputs (0major+1269minor)pagefaults 0swaps
	Code: 0
	Value: IntegerValue(100000)

python src/main/tiger-interpreter.py src/benchmark/while-10k.tig
	Time: 0.05user 0.00system 0:00.06elapsed 100%CPU (0avgtext+0avgdata 7548maxresident)k 0inputs+0outputs (0major+1011minor)pagefaults 0swaps
	Code: 0
	Value: IntegerValue(10000)

bin/tiger-interpreter-no-jit src/benchmark/while-10k.tig
	Time: 0.00user 0.00system 0:00.00elapsed 50%CPU (0avgtext+0avgdata 6116maxresident)k 0inputs+0outputs (0major+1141minor)pagefaults 0swaps
	Code: 0
	Value: IntegerValue(10000)

bin/tiger-interpreter src/benchmark/while-10k.tig
	Time: 0.00user 0.00system 0:00.00elapsed 66%CPU (0avgtext+0avgdata 9916maxresident)k 0inputs+64outputs (0major+1268minor)pagefaults 0swaps
	Code: 0
	Value: IntegerValue(10000)

python src/main/tiger-interpreter.py src/benchmark/while-1k.tig
	Time: 0.01user 0.00system 0:00.02elapsed 95%CPU (0avgtext+0avgdata 7516maxresident)k 0inputs+0outputs (0major+1011minor)pagefaults 0swaps
	Code: 0
	Value: IntegerValue(1000)

bin/tiger-interpreter-no-jit src/benchmark/while-1k.tig
	Time: 0.00user 0.00system 0:00.00elapsed 0%CPU (0avgtext+0avgdata 2612maxresident)k 0inputs+0outputs (0major+270minor)pagefaults 0swaps
	Code: 0
	Value: IntegerValue(1000)

bin/tiger-interpreter src/benchmark/while-1k.tig
	Time: 0.00user 0.00system 0:00.00elapsed 50%CPU (0avgtext+0avgdata 7056maxresident)k 0inputs+64outputs (0major+569minor)pagefaults 0swaps
	Code: 0
	Value: IntegerValue(1000)

python src/main/tiger-interpreter.py src/benchmark/while-1m.tig
	Time: 5.44user 0.00system 0:05.45elapsed 99%CPU (0avgtext+0avgdata 7544maxresident)k 0inputs+0outputs (0major+1010minor)pagefaults 0swaps
	Code: 0
	Value: IntegerValue(1000000)

bin/tiger-interpreter-no-jit src/benchmark/while-1m.tig
	Time: 0.10user 0.00system 0:00.11elapsed 89%CPU (0avgtext+0avgdata 6148maxresident)k 0inputs+0outputs (0major+1151minor)pagefaults 0swaps
	Code: 0
	Value: IntegerValue(1000000)

bin/tiger-interpreter src/benchmark/while-1m.tig
	Time: 0.11user 0.00system 0:00.11elapsed 100%CPU (0avgtext+0avgdata 10088maxresident)k 0inputs+64outputs (0major+1290minor)pagefaults 0swaps
	Code: 0
	Value: IntegerValue(1000000)

