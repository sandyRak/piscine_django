def my_var():
  a = 42
  b = "42"
  c = "quarante-deux"
  d = 42.0
  e = True
  f = [42]
  g = {42: 42}
  h = (42,)
  i = set()

  variables = [a, b, c, d, e, f, g, h, i]

  for var in variables:
    print(f"{var} has a type {type(var)}")

if __name__ == '__main__':
  my_var()