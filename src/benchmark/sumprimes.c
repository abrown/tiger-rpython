#include <stdio.h>
#include <stdlib.h>

int main(int argc, const char* argv[]) {
    if (argc < 2) {
        printf("Expected usage: sumprimes [number of loops]\n");
        return 1;
    }

    int max = atoi(argv[1]);
    int s = 0;
    int n = 2;
    // int i = 0;  // for counting the number of inner loops executed

    while (n <= max) {
        int p = 1;
        int d = 2;
        while (d <= (n - 1)){
            int m = d * (n / d);
            if (n <= m) {
                p = 0;
            }
            d += 1;
            // i += 1;
        }
        if (p) {
            s += n;
        }
        n += 1;
    }
    // printf("%d\n", i);
    printf("%d\n", s);

	return 0;
}