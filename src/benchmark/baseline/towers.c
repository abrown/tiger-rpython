#include <stdio.h>
#include <stdlib.h>

int main(int argc, const char* argv[]) {
  typedef struct TowersDisk { int size; struct TowersDisk *next; } TowersDisk;
  int numberOfDisks = 22;
  TowersDisk *piles[3] = {NULL, NULL, NULL};
  int movesDone = 0;

  void pushDisk(TowersDisk *disk, int pile) {
    TowersDisk *top = piles[pile];
    disk->next = top;
    piles[pile] = disk;
  }

  TowersDisk *popDiskFrom(int pile) {
    TowersDisk *top = piles[pile];
    piles[pile] = top->next;
    top->next = NULL;
    return top;
  }

  void moveTopDisk(int fromPile, int toPile) {
    pushDisk(popDiskFrom(fromPile), toPile);
    movesDone = movesDone + 1;
  }

  void buildTowerAt(int pile, int disks) {
    int i;
    for (i = 0; i <= disks; i++) {
      TowersDisk *disk = malloc(sizeof(TowersDisk));
      disk->size = i;
      disk->next = NULL;
      pushDisk(disk, pile);
    }
  }

  void moveDisks(int disks, int fromPile, int toPile) {
    if(disks == 1) {
      moveTopDisk(fromPile, toPile);
    } else {
      int otherPile = (3 - fromPile) - toPile;
      moveDisks(disks - 1, fromPile, otherPile);
      moveTopDisk(fromPile, toPile);
      moveDisks(disks - 1, otherPile, toPile);
    }
  }

  buildTowerAt(0, numberOfDisks);
  movesDone = 0;
  moveDisks(numberOfDisks, 0, 1);
  printf("%d\n", movesDone);
}