#include <stdio.h>
#include <string.h>

int main(int argc, const char* argv[]) {
  int stringSize = 9;
  int count = 0;
  int v[stringSize];  // typedef this as vector?
  memset(v, 0, stringSize * sizeof(int));

  void swap(int i, int j) {
    int tmp = v[i];
    v[i] = v[j];
    v[j] = tmp;
  }

  void permute(int n) {
    count = count + 1;
    if (n != 0) {
      int n1 = n - 1;
      permute(n1);
      int i = n1;  // TODO remove?
      while (i >= 0) {
        swap(n1, i);
        permute(n1);
        swap(n1, i);
        i = i - 1;
      }
    }
  }

  permute(stringSize);
  printf("%d\n", count);
}