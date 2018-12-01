#include <stdio.h>
#include <string.h>

int main(int argc, const char* argv[]) {
  int max = 10000;
  int s = 0;
  int n = 2;

  while (n <= max) {
    int p = 1;
    int d = 2;
    while (d <= (n - 1)) {
      int m = d * (n / d);
      if (n <= m) {
        p = 0;
      }
      d = d + 1;
    }
    if (p != 0) {
      s = s + n;
    }
    n = n + 1;
  }

  printf("%d\n", s);
}