#!/usr/bin/env bash

for f in $(ls *.tig);
  do echo -e "for i := 0 to 30\ndo (\n  timeGo();\n$(sed 's/^/  /' $f);\n  timeStop()\n)" > $f;
done

