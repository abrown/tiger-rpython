Environments
============

Due to how much effect the environment implementation has on performance, multiple environment implementations are 
retained here. The implementation is selected in the `environment.py` file. I made an honest attempt to maintain the 
same interface over different implementations but this was relatively difficult with the switch to using paths, so the 
usage is slightly different. The implementations are:

 - dictionary tree: variables are retrieved using their string name from a hash table. Each level has a pointer to its
 enclosing level: if not found, the search searches successively up the enclosing scopes.
 - paths: instead of string names, a tuple with `(level offset, index in level)` is calculated statically and assigned 
 to each lvalue; on lookup, the search traverses `level offset` levels and then retrieves the `index` at this level
 - paths without display: looking at RPython traces, the object enclosing the parallel tree of expression and type 
 levels was introducing overhead in the form of extra operations. This change removes the global display object and 
 operates on the levels directly