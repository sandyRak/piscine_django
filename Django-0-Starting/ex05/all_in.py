import sys

def get_dict():
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
  return states , capital_cities

def format_text(text):
  return " ".join(text.split()).lower()

def search_string(args):
  states, capitals = get_dict()
  capital_inverse={valeur:cle for cle, valeur in capitals.items()}
  state_inverse = {valeur:cle for cle, valeur in states.items()}
  if len(args) != 2:
    return
  text_list = args[1].split(",")
  for str in text_list:
    str = format_text(str)
    if str == "":
            continue
    if str.title() in (capital_inverse):
      state = capital_inverse[str.title()]
      print(str.title() ,"is the capital of ", state_inverse[state])
    elif str.title() in (states) :
      capital = states[str.title()]
      print(capitals[capital] , "is the capital of ", str.title())
    else:
      print(str, "is neither a capital city nor a state")
  
if __name__ == "__main__":
  search_string(sys.argv)



