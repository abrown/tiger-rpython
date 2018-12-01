#include <stdio.h>
#include <string.h>

int main(int argc, const char* argv[]) {
  int max = 10000000;

  int sieve(int size, int *flags) {
    int primeCount = 0;
    int i;
    for(i = 2; i <= size; i++) {
      if(flags[i-1] == 1) {
        primeCount = primeCount + 1;
        int k = i + i;
        while(k <= size) {
          flags[k-1] = 0;
          k = k + i;
        }
      }
    }
    return primeCount;
  }

  int flags[max];
  int i;
  for(i = 0; i < max; i++) flags[i] = 1;

  int result = sieve(max, flags);
  printf("%d\n", result);
}