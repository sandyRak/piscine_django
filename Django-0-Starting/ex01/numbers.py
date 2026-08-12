def read_numbers(filename):
  with open(filename, "r") as f:
    content = f.read()
  numbers = content.strip().split(",")
  return numbers 

def print_numbers(numbers):
  for number in numbers :
    print(number.strip())

def numbers(filename):
  numbers_list = read_numbers(filename)
  print_numbers(numbers_list)

if __name__ == '__main__':
  numbers("numbers.txt")