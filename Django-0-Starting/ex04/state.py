import sys

def print_state(args):
  states = {
    "Oregon" : "OR",
    "Alabama" : "AL",
    "New Jersey": "NJ",
    "Colorado" : "CO"
  }
  capital_cities = {
    "OR": "Salem",
    "AL": "Montgomery",
    "NJ": "Trenton",
    "CO": "Denver"
  }

  inv_states ={valeur:cle for cle, valeur in states.items()}
  inv_capitals = {valeur:cle for cle, valeur in capital_cities.items()}
  if len(args) != 2:
    return
  if args[1] in capital_cities.values():
    print(inv_states[inv_capitals[args[1]]])
  else:
    print("Unknown capital city")

if __name__ == "__main__":
  print_state(sys.argv)