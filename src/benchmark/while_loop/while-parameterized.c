#include <stdio.h>
#include <stdlib.h>

int main(int argc, const char* argv[]) {
    if (argc < 2) {
        printf("Expected usage: while [number of loops]\n");
        return 1;
    }

    int n = atoi(argv[1]);
    int i = 0;
    while (i < n) {
        i++;
    }

    printf("%d\n", i);
	return 0;
}