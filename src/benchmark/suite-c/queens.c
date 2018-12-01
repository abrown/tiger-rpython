#include <stdio.h>
#include <string.h>

int main(int argc, const char* argv[]) {
  int queens(int n) {
    int m = n - 1;
    int i;
    int freeRows[n];
    for(i = 0; i < n; i++) freeRows[i] = 1;
    int freeMaxs[2 * n];
    for(i = 0; i < 2 * n; i++) freeMaxs[i] = 1;
    int freeMins[2 * n];
    for(i = 0; i < 2 * n; i++) freeMins[i] = 1;
    int queenRows[n];
    for(i = 0; i < n; i++) queenRows[i] = -1;

    void printBoard() {
      int r, c;
      for (r = 0; r <= m; r++) {
        for (c = 0; c <= m; c++) {
          if(queenRows[r] == c){
            printf(" X");
          } else {
            printf(" .");
          }
        }
        printf("\n");
      }
      printf("\n");
    }

    int getRowColumn(int r, int c) {
      // printf("%d + %d + %d ?= 3\n", freeRows[r], freeMaxs[c + r], freeMins[c - r + m]);
      if ((freeRows[r] + freeMaxs[c + r] + freeMins[c - r + m]) == 3) {
        return 1;
      } else {
        return 0; // TODO simplify
      }
    }

    void setRowColumn(int r, int c, int v) {
      freeRows[r] = v;
      freeMaxs[c + r] = v;
      freeMins[c - r + m] = v;
    }

    int placeQueen(int c) {
      int placed = 0;
      int r;
      for (r = 0; r <= m; r++) {
        if(getRowColumn(r, c) == 1) {
          queenRows[r] = c;
          setRowColumn(r, c, 0);
          if (c == m) {
            placed = 1;
            break;
          }
          if (placeQueen(c + 1) == 1) {
            placed = 1;
            break;
          }
          setRowColumn(r, c, 1);
        }
      }
      return placed;
    }

    int result = placeQueen(0);
    printBoard();
    return result;
  }

  int i;
  for(i = 0; i <= 20; i++) {
    queens(i);
  }
}