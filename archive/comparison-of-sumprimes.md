E2 vs Tiger
===========

JIT-ed E2 is 33x faster than JIT-ed Tiger

```
abrown@abrown-desk:~/Code/e2-benchmark$ make benchmarks
mkdir -p var

PYPYLOG=jit:var/e2-slow.log /usr/bin/time bin/e2-slow sumprimes-10k.e2
5736396
5.87user 0.00system 0:05.90elapsed 99%CPU (0avgtext+0avgdata 42512maxresident)k
0inputs+4112outputs (0major+9584minor)pagefaults 0swaps

PYPYLOG=jit:var/e2-fast.log /usr/bin/time bin/e2-fast sumprimes-10k.e2
5736396
0.34user 0.00system 0:00.36elapsed 96%CPU (0avgtext+0avgdata 9972maxresident)k
0inputs+208outputs (0major+1300minor)pagefaults 0swaps
```

```
abrown@abrown-desk:~/Code/tiger-rpython$ make benchmarks-sumprimes 
./src/benchmark/benchmark.sh src/benchmark/sumprimes-10k.tig
bin/tiger-interpreter-no-jit src/benchmark/sumprimes-10k.tig
        Time: 17.21user 0.01system 0:17.25elapsed 99%CPU (0avgtext+0avgdata 38512maxresident)k 0inputs+0outputs (0major+9245minor)pagefaults 0swaps
        Code: 0
        Value: 5736396

bin/tiger-interpreter src/benchmark/sumprimes-10k.tig
        Time: 11.33user 0.01system 0:11.37elapsed 99%CPU (0avgtext+0avgdata 33472maxresident)k 0inputs+1048outputs (0major+7153minor)pagefaults 0swaps
        Code: 0
        Value: 5736396
```



Why?
----

E2: 

```
[f7012bb9bcc61] {jit-summary
Tracing:      	8	0.001631
Backend:      	8	0.001297
TOTAL:      		0.348161
ops:             	204
recorded ops:    	203
  calls:         	53
guards:          	78
opt ops:         	253
opt guards:      	55
opt guards shared:	22
forcings:        	0
abort: trace too long:	0
abort: compiling:	0
abort: vable escape:	0
abort: bad loop: 	0
abort: force quasi-immut:	0
nvirtuals:       	0
nvholes:         	0
nvreused:        	0
vecopt tried:    	0
vecopt success:  	0
Total # of loops:	2
Total # of bridges:	6
Freed # of loops:	0
Freed # of bridges:	0
[f7012bb9c8155] jit-summary}
```

Tiger

```
[f6deef41558f7] {jit-summary
Tracing:      	5	0.004237
Backend:      	5	0.004544
TOTAL:      		11.359359
ops:             	846
recorded ops:    	745
  calls:         	45
guards:          	223
opt ops:         	1268
opt guards:      	364
opt guards shared:	269
forcings:        	0
abort: trace too long:	0
abort: compiling:	0
abort: vable escape:	0
abort: bad loop: 	0
abort: force quasi-immut:	0
nvirtuals:       	540
nvholes:         	204
nvreused:        	268
vecopt tried:    	0
vecopt success:  	0
Total # of loops:	2
Total # of bridges:	3
Freed # of loops:	0
Freed # of bridges:	0
[f6deef416131b] jit-summary}
```

For example, the inner loop on `d` in E2 is 36 operations with 2 `call_i` for the division whereas Tiger, for the same
loop, has 488 operations and 40 `call_*` (mostly for Environment.__locate__ [18] and dictionary operations [18]).