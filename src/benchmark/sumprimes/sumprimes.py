max = 10000
s = 0
n = 2
# i = 0  # for counting the number of inner loops execution

while n <= max:
    p = 1
    d = 2
    while d <= (n - 1):
        m = d * (n / d)
        if n <= m:
            p = 0
        d += 1
        # i += 1
    if p:
        s += n
    n += 1

# print(i)
print(s)
