def f(*args):
    return args

print(f(1, 2, 3, 4, 5))


def f(**kwargs):
    return kwargs

print(f(a=1, b=2, c=3))

